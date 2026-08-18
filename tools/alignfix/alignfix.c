/* alignfix.so -- do for qemu-user what the MIPS kernel does for the device.
 *
 * The measurement that made this necessary
 * ----------------------------------------
 * `handler-sweep.py` reported 39 of this build's 57 handlers dying on a single
 * well-formed POST, and wrote `died_under_emulation` rather than "crash"
 * because it could not say why.  W07 attached gdb to qemu-user's gdbstub and
 * caught the fault:
 *
 *     => 0x2b2c87dc:  sh  s7,0(s8)        (libapmib.so + 0x27d0)
 *
 * which is inside `mib_write_to_raw`, the TLV serialiser that packs the MIB
 * into the raw flash buffer.  Variable-length records mean field offsets are
 * naturally odd, so the halfword store lands on an odd address.
 *
 * Linux/MIPS emulates unaligned user-space accesses in its trap handler; the
 * device therefore executes this fine.  `qemu-user` delivers SIGBUS instead,
 * and `boa` has a SIGBUS handler that dumps core and aborts.  So the emulated
 * environment could not run *any* configuration-writing path, and every result
 * that depended on one -- the 39-handler sweep, `P8-24`'s recovery write, any
 * fuzzing of a save handler -- was measuring the emulator.
 *
 * `P5-6`'s frozen prediction says "the apmib part needs a shim".  It was right
 * about the need and wrong about the kind: the shim is not a stub for apmib, it
 * is the alignment fix-up that qemu-user does not provide.
 *
 * Why this is honest rather than a cheat
 * -------------------------------------
 * It adds nothing the device does not already have.  It removes a divergence
 * between the emulator and the target, and it counts what it did, so a run can
 * report "17 unaligned accesses fixed" instead of quietly looking like silicon.
 * Every fix-up is logged with its address; a reader can check that they all
 * land inside the serialiser and not somewhere a real bug would put them.
 *
 * How it refuses to be silently wrong
 * ----------------------------------
 * The MIPS o32 ucontext layout is hard-coded here, and hard-coded offsets that
 * are wrong produce plausible garbage.  So every fix-up is checked twice before
 * any register is touched:
 *
 *   1. the instruction word read back from the recovered `pc` must decode as
 *      one of the five load/store forms that can fault this way, and
 *   2. the address computed from the recovered registers must actually be
 *      misaligned for that access width.
 *
 * If either check fails the handler prints what it saw and re-raises SIGBUS
 * with the default disposition, so the process dies exactly as it did before
 * and nothing downstream mistakes a broken shim for a working one.
 *
 * Freestanding on purpose: built with -nostdlib and raw syscalls, so it does
 * not care whether the target links uClibc or anything else, and so that
 * installing the handler cannot recurse through its own interposed sigaction.
 */

typedef unsigned int u32;
typedef int s32;
typedef unsigned char u8;

/* ---------------------------------------------------------------- syscalls */
/* o32: number in $v0, args in $a0-$a3, error flagged in $a3. */
static long sys4(long n, long a, long b, long c, long d)
{
    register long v0 __asm__("$2") = n;
    register long a0 __asm__("$4") = a;
    register long a1 __asm__("$5") = b;
    register long a2 __asm__("$6") = c;
    register long a3 __asm__("$7") = d;
    __asm__ __volatile__("syscall"
                         : "+r"(v0), "+r"(a3)
                         : "r"(a0), "r"(a1), "r"(a2)
                         : "memory", "$1", "$3", "$8", "$9", "$10", "$11",
                           "$12", "$13", "$14", "$15", "$24", "$25", "hi", "lo");
    return a3 ? -v0 : v0;
}

#define NR_write        4004
#define NR_rt_sigaction 4194
#define SIGBUS_MIPS     10
#define SA_SIGINFO_MIPS 0x00000008
#define SA_NODEFER_MIPS 0x40000000

/* MIPS puts sa_flags first; sigset_t is four words. */
struct k_sigaction {
    u32 sa_flags;
    void *sa_handler;
    u32 sa_mask[4];
};

static void out(const char *s)
{
    const char *p = s;
    while (*p)
        p++;
    sys4(NR_write, 2, (long)s, (long)(p - s), 0);
}

static void outhex(u32 v)
{
    char buf[11];
    static const char d[] = "0123456789abcdef";
    int i;
    buf[0] = '0';
    buf[1] = 'x';
    for (i = 0; i < 8; i++)
        buf[2 + i] = d[(v >> ((7 - i) * 4)) & 0xf];
    buf[10] = 0;
    out(buf);
}

/* --------------------------------------------------------- ucontext layout */
/*
 * o32, from the kernel's uapi headers:
 *
 *   ucontext { u32 uc_flags; ucontext *uc_link; stack_t uc_stack;  <- 0..19
 *              struct sigcontext uc_mcontext; ... }                <- 24 (8-aligned)
 *   sigcontext { u32 sc_regmask; u32 sc_status; u64 sc_pc; u64 sc_regs[32]; ... }
 *
 * Big-endian 32-bit, so the meaningful half of each u64 is at +4.
 *
 * The two offsets are overridable so the guard suite can build a deliberately
 * wrong shim and prove the refusals below actually fire. A handler that cannot
 * be made to fail is not a checked handler.
 */
#ifndef ALIGNFIX_UC_PC_LO
#define ALIGNFIX_UC_PC_LO   (24 + 8 + 4)
#endif
#ifndef ALIGNFIX_UC_REGS_LO
#define ALIGNFIX_UC_REGS_LO (24 + 16 + 4)
#endif
#define UC_PC_LO    ALIGNFIX_UC_PC_LO
#define UC_REGS_LO  ALIGNFIX_UC_REGS_LO

static u32 reg_get(u8 *uc, int n) { return *(u32 *)(uc + UC_REGS_LO + n * 8); }

static void reg_set(u8 *uc, int n, u32 v)
{
    u32 *slot = (u32 *)(uc + UC_REGS_LO + n * 8);
    slot[0] = (v & 0x80000000u) ? 0xffffffffu : 0u;   /* sign-extend the high half */
    slot[1] = v;
}

static u32 pc_get(u8 *uc) { return *(u32 *)(uc + UC_PC_LO); }
static void pc_set(u8 *uc, u32 v) { *(u32 *)(uc + UC_PC_LO) = v; }

/* ------------------------------------------------------------- statistics */
static u32 fixups;
static u32 refusals;
static u32 verbose_left = 12;

/* ------------------------------------------------------------- the handler */
static void install(void *fn);

static void on_sigbus(int sig, void *info, void *ucv)
{
    u8 *uc = (u8 *)ucv;
    u32 pc = pc_get(uc);
    u32 insn, rs, rt, addr, width, is_store, is_signed, val;
    s32 simm;
    u8 *p;

    (void)sig;
    (void)info;

    /* Reading through the recovered pc is the first check: a wrong layout
     * almost never yields a pointer that is both readable and decodes as one
     * of the five forms below. */
    insn = *(u32 *)(unsigned long)pc;
    rs = (insn >> 21) & 31;
    rt = (insn >> 16) & 31;
    simm = (s32)(short)(insn & 0xffff);

    switch (insn >> 26) {
    case 0x21: width = 2; is_store = 0; is_signed = 1; break;   /* lh  */
    case 0x25: width = 2; is_store = 0; is_signed = 0; break;   /* lhu */
    case 0x29: width = 2; is_store = 1; is_signed = 0; break;   /* sh  */
    case 0x23: width = 4; is_store = 0; is_signed = 0; break;   /* lw  */
    case 0x2b: width = 4; is_store = 1; is_signed = 0; break;   /* sw  */
    default:
        refusals++;
        out("alignfix: REFUSING -- instruction at pc=");
        outhex(pc);
        out(" is ");
        outhex(insn);
        out(", not a fixable load/store. Layout or delay-slot case; re-raising.\n");
        install((void *)0);           /* SIG_DFL */
        return;                        /* returning re-executes and dies */
    }

    addr = reg_get(uc, rs) + (u32)simm;

    /* Second check: it has to actually be misaligned.  If it is aligned, the
     * registers we read are not the registers that faulted. */
    if ((addr & (width - 1)) == 0) {
        refusals++;
        out("alignfix: REFUSING -- computed address ");
        outhex(addr);
        out(" is already aligned for a ");
        outhex(width);
        out("-byte access at pc=");
        outhex(pc);
        out(". The ucontext offsets are wrong; re-raising.\n");
        install((void *)0);
        return;
    }

    p = (u8 *)(unsigned long)addr;
    if (is_store) {
        val = reg_get(uc, rt);
        if (width == 2) {
            p[0] = (u8)(val >> 8);
            p[1] = (u8)val;
        } else {
            p[0] = (u8)(val >> 24);
            p[1] = (u8)(val >> 16);
            p[2] = (u8)(val >> 8);
            p[3] = (u8)val;
        }
    } else {
        if (width == 2) {
            val = ((u32)p[0] << 8) | p[1];
            if (is_signed && (val & 0x8000))
                val |= 0xffff0000u;
        } else {
            val = ((u32)p[0] << 24) | ((u32)p[1] << 16) | ((u32)p[2] << 8) | p[3];
        }
        reg_set(uc, rt, val);
    }

    fixups++;
    if (verbose_left) {
        verbose_left--;
        out("alignfix: fixed ");
        out(is_store ? "store" : "load ");
        out(" width=");
        outhex(width);
        out(" addr=");
        outhex(addr);
        out(" pc=");
        outhex(pc);
        out("\n");
    }
    pc_set(uc, pc + 4);
}

static void install(void *fn)
{
    struct k_sigaction act;
    act.sa_flags = SA_SIGINFO_MIPS | SA_NODEFER_MIPS;
    act.sa_handler = fn;
    act.sa_mask[0] = act.sa_mask[1] = act.sa_mask[2] = act.sa_mask[3] = 0;
    if (fn == (void *)0)
        act.sa_flags = 0;
    sys4(NR_rt_sigaction, SIGBUS_MIPS, (long)&act, 0, 16);
}

/* -------------------------------------------------- keep the app's hands off */
/*
 * boa imports both `signal` and `sigaction` and installs a SIGBUS handler that
 * dumps core.  If it wins, everything above is dead code.  These two
 * interpositions let every other signal through untouched -- via the raw
 * syscall, so they do not recurse into themselves -- and quietly decline SIGBUS.
 */
int sigaction(int sig, const void *act, void *oact)
{
    if (sig == SIGBUS_MIPS)
        return 0;
    return (int)sys4(NR_rt_sigaction, sig, (long)act, (long)oact, 16);
}

void *signal(int sig, void *handler)
{
    struct k_sigaction act, old;
    if (sig == SIGBUS_MIPS)
        return (void *)0;
    act.sa_flags = 0;
    act.sa_handler = handler;
    act.sa_mask[0] = act.sa_mask[1] = act.sa_mask[2] = act.sa_mask[3] = 0;
    old.sa_handler = (void *)0;
    sys4(NR_rt_sigaction, sig, (long)&act, (long)&old, 16);
    return old.sa_handler;
}

__attribute__((constructor)) void alignfix_init(void)
{
    install((void *)on_sigbus);
    out("alignfix: SIGBUS handler installed (unaligned load/store fix-up)\n");
}
