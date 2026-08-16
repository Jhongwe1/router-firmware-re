/* BoaGate.java — three rules, run as a build gate, with a positive control.
 *
 * Why this exists, and why it is not a fifth report
 * -------------------------------------------------
 * Every other script here answers "what is in this binary". This one answers a
 * different question: **would this build have shipped, if the vendor had run a
 * check on it.** W08's "if I were building this router" chapter was planned as
 * prose — five defensive recommendations. Prose is free. A gate that runs, and
 * that has been shown to fire on a build known to be defective, is not.
 *
 * The three rules
 * ---------------
 *   R1  a request parameter reaching strcpy/strcat/sprintf with no bound
 *   R2  a request parameter reaching system()/popen(), directly or through a
 *       buffer filled in the same function
 *   R3  a request parameter copied into a fixed-size global (.bss/.data) object
 *
 * R2 is the one with teeth, and it is the reason this is a separate script
 * rather than a filter over BoaArgTrace's output.
 *
 * On the build this device runs, the command injection looks like this:
 *
 *     cmd = req_get_cstream_var(req, "sysCmd", "");
 *     snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log");
 *     system(buf);
 *
 * The tainted argument is on the **snprintf**. `system`'s argument is `buf` — a
 * stack address, with no SSA dependency on `cmd` at all, because the connection
 * is through memory. A rule that inspects the arguments of `system()` sees a
 * stack pointer and reports nothing.
 *
 * That is not a hypothetical: BoaArgTrace, run over this binary, reports exactly
 * one request-parameter row for formSysCmd and it is on the snprintf. **A gate
 * built from that output alone would pass the only unauthenticated RCE in the
 * firmware.**
 *
 * So R2 works in two steps, within one function:
 *   1. collect every write-destination that a request parameter reaches, as a
 *      stack offset or a global address;
 *   2. for each system()/popen(), resolve its argument to the same kind of
 *      location and check the set.
 *
 * Same-function only. That is a deliberate underestimate: it cannot follow a
 * buffer passed to a helper, so the count is a floor, not a total. A gate that
 * overstates is one nobody keeps running.
 *
 * The positive control, which matters more than the three rules
 * ------------------------------------------------------------
 * A SAST rule that has never fired on a build known to be defective is not a
 * check, it is a decoration. This project's own record is the argument: three
 * of the instrument bugs in PROGRESS.md were checks that could not fail, and
 * every one of them reported success for months.
 *
 * So this script takes `control:<label>=<N>` and **fails if the named build does
 * not produce at least N findings**. V2.1.2 is the control because W03 and W04
 * established, by hand and at instruction level, that it contains the
 * `submit-url` idiom in 34 handlers and unfiltered `system()` in formWsc. If the
 * gate comes back clean on that build, the gate is broken — the build is not.
 *
 * Usage:
 *   -postScript BoaGate.java <out.json> <sha256|-> [accessor:FUN_xxxxxxxx]
 *                                                 [control:N] [depth:N]
 */

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;

public class BoaGate extends GhidraScript {

    private static final int TIMEOUT_SECONDS = 120;

    /** Unbounded copy/format sinks: destination is argument 0. */
    private static final String[] UNBOUNDED_WRITE = { "strcpy", "strcat", "sprintf" };
    /** Bounded equivalents: still taint the destination, but do not trip R1. */
    private static final String[] BOUNDED_WRITE = { "strncpy", "strncat", "snprintf" };
    /** Command execution: argument 0 is handed to a shell. */
    private static final String[] EXEC = { "system", "popen" };

    private DecompInterface decomp;
    private int walkDepth = 8;
    private String accessorOverride = "";
    private int accessorMatches = 0;
    private int controlMinimum = -1;

    /**
     * sink name -> every address a call to it can land on, from BoaPlt.
     *
     * Not a name comparison, and the difference is not stylistic. The first
     * version of this script identified sinks by comparing the callee's *name*
     * against "strcpy". On these binaries a libc call goes through a PLT stub
     * that Ghidra names FUN_xxxxxxxx, because sstrip removed the section headers
     * that would let it find .plt -- so nothing matched and the gate returned
     * **zero findings on V2.1.2**, a build W03 and W04 read by hand and found
     * defective in 34 handlers.
     *
     * That is the third appearance of this exact bug (BoaSinks in W03,
     * BoaArgTrace in W04, here). Both earlier times it shipped and was caught
     * later by comparing two builds. This time the positive control caught it on
     * the first run, before a single number left the script -- which is the
     * whole argument for having one.
     *
     * BoaPlt.java exists so there is one resolver. Re-implementing it is what
     * went wrong in W04, and name-matching was the same mistake in a cheaper
     * disguise.
     */
    private final Map<String, Set<Address>> sinkTargets = new LinkedHashMap<>();
    private final Set<Address> accessorTargets = new LinkedHashSet<>();
    private final List<String> unresolvedSinks = new ArrayList<>();
    private int callSites = 0;

    /** A resolved location a value was written to, so R2 can match them up. */
    private static final class Loc {
        final String kind;       // "stack" | "global"
        final long value;        // stack offset, or global address

        Loc(String kind, long value) {
            this.kind = kind;
            this.value = value;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Loc && ((Loc) o).kind.equals(kind) && ((Loc) o).value == value;
        }

        @Override
        public int hashCode() {
            return kind.hashCode() * 31 + Long.hashCode(value);
        }

        @Override
        public String toString() {
            return "stack".equals(kind) ? String.format("sp%+d", value)
                                        : String.format("%08x", value);
        }
    }

    private static final class Finding {
        String rule, sink, site, function, entry, parameter, detail;
        int destSize = -1;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "gate.json";
        String sha = args.length > 1 && !"-".equals(args[1]) ? args[1] : "";
        for (int i = 2; i < args.length; i++) {
            String s = args[i];
            if (s.startsWith("accessor:"))    { accessorOverride = s.substring(9); }
            else if (s.startsWith("control:")) { controlMinimum = Integer.parseInt(s.substring(8)); }
            else if (s.startsWith("depth:"))   { walkDepth = Integer.parseInt(s.substring(6)); }
        }

        decomp = new DecompInterface();
        decomp.setOptions(new DecompileOptions());
        if (!decomp.openProgram(currentProgram)) {
            throw new Exception("decompiler would not open: " + decomp.getLastMessage());
        }

        // Resolve every sink through BoaPlt before scanning anything.
        List<String> allSinks = new ArrayList<>();
        for (String[] group : new String[][] { UNBOUNDED_WRITE, BOUNDED_WRITE, EXEC }) {
            for (String n : group) {
                allSinks.add(n);
            }
        }
        for (String n : allSinks) {
            Set<Address> t = BoaPlt.callTargets(this, n);
            sinkTargets.put(n, t);
            if (t.isEmpty()) {
                unresolvedSinks.add(n);
            }
        }
        if (!accessorOverride.isEmpty()) {
            accessorTargets.addAll(BoaPlt.callTargets(this, accessorOverride));
        }

        // Group call sites by containing function, from *references* to the
        // resolved sink addresses. Not by walking pcode and reading each CALL's
        // target: on MIPS PIC every libc call is `jalr t9`, so the pcode target
        // is a register load and comparing it against a resolved address matches
        // nothing. That is how the second version of this script also returned
        // zero findings on the control build -- a different mechanism, the same
        // symptom, caught the same way.
        Map<Function, List<Object[]>> byFunction = new LinkedHashMap<>();
        int siteCount = 0;
        for (var kv : sinkTargets.entrySet()) {
            for (Address t : kv.getValue()) {
                for (var r : getReferencesTo(t)) {
                    if (!r.getReferenceType().isCall() && !r.getReferenceType().isJump()) {
                        continue;
                    }
                    Function caller = getFunctionContaining(r.getFromAddress());
                    if (caller == null || BoaPlt.isStub(this, caller)) {
                        continue;
                    }
                    byFunction.computeIfAbsent(caller, x -> new ArrayList<>())
                              .add(new Object[] { r.getFromAddress(), kv.getKey() });
                    siteCount++;
                }
            }
        }

        List<Finding> findings = new ArrayList<>();
        int functionsScanned = 0;
        int functionsFailed = 0;

        for (var kv : byFunction.entrySet()) {
            monitor.checkCancelled();
            Function fn = kv.getKey();
            DecompileResults res = decomp.decompileFunction(fn, TIMEOUT_SECONDS, monitor);
            if (res == null || !res.decompileCompleted() || res.getHighFunction() == null) {
                functionsFailed++;
                continue;
            }
            functionsScanned++;
            List<Object[]> sites = kv.getValue();
            sites.sort((a, b) -> ((Address) a[0]).compareTo((Address) b[0]));
            scan(fn, res.getHighFunction(), sites, findings);
        }
        this.callSites = siteCount;

        writeJson(outPath, sha, findings, functionsScanned, functionsFailed);

        Map<String, Integer> byRule = new LinkedHashMap<>();
        for (Finding f : findings) {
            byRule.merge(f.rule, 1, Integer::sum);
        }
        println(String.format(
            "BoaGate: %d findings %s over %d functions (%d would not decompile), wrote %s",
            findings.size(), byRule, functionsScanned, functionsFailed, outPath));
    }

    // ------------------------------------------------------------------ scan

    private void scan(Function fn, HighFunction hf, List<Object[]> sites, List<Finding> findings) {
        // Pass 1: every location a request parameter is written into, and the
        // parameter name responsible. Bounded writes are recorded too -- they do
        // not trip R1, but a bounded copy of attacker data into a buffer that is
        // then handed to a shell is still command injection. That is exactly the
        // formSysCmd shape: snprintf(buf, 100, "%s ...", sysCmd); system(buf).
        Map<Loc, String> tainted = new LinkedHashMap<>();
        Map<Loc, Address> taintedAt = new LinkedHashMap<>();
        List<Object[]> execCalls = new ArrayList<>();

        for (Object[] site : sites) {
            Address at = (Address) site[0];
            String bare = (String) site[1];
            PcodeOpAST op = callOpAt(hf, at);
            if (op == null) {
                continue;
            }

            if (in(bare, EXEC)) {
                execCalls.add(new Object[] { at, bare, op });
                continue;
            }

            boolean unbounded = in(bare, UNBOUNDED_WRITE);
            boolean bounded = in(bare, BOUNDED_WRITE);
            if (!unbounded && !bounded) {
                continue;
            }

            // Which request parameter, if any, reaches this call's inputs?
            Set<String> params = new LinkedHashSet<>();
            for (int i = 1; i < op.getNumInputs(); i++) {
                collectParams(op.getInput(i), walkDepth, params);
            }
            if (params.isEmpty()) {
                continue;
            }
            String param = String.join(",", params);

            Loc dest = locOf(op.getNumInputs() > 1 ? op.getInput(1) : null, walkDepth);
            if (dest != null) {
                tainted.put(dest, param);
                taintedAt.put(dest, at);
            }

            if (unbounded) {
                Finding f = new Finding();
                f.rule = "R1";
                f.sink = bare;
                f.site = at.toString();
                f.function = fn.getName();
                f.entry = fn.getEntryPoint().toString();
                f.parameter = param;
                f.detail = "request parameter reaches an unbounded write"
                         + (dest == null ? "" : ", destination " + dest);
                findings.add(f);
            }

            // R3: the destination is a fixed-size global rather than a stack
            // slot. lastUrl[100] followed by needReboot is the shape; the size
            // comes from the symbol, not from a guess.
            if (dest != null && "global".equals(dest.kind)) {
                int size = globalSize(dest.value);
                Finding f = new Finding();
                f.rule = "R3";
                f.sink = bare;
                f.site = at.toString();
                f.function = fn.getName();
                f.entry = fn.getEntryPoint().toString();
                f.parameter = param;
                f.destSize = size;
                f.detail = "request parameter copied into fixed-size global "
                         + symbolAt(dest.value) + " @ " + dest
                         + (size > 0 ? " (" + size + " bytes)" : " (size unknown)");
                findings.add(f);
            }
        }

        // Pass 2: R2. Direct taint on the exec argument, or the exec argument
        // naming a location pass 1 saw a request parameter written into.
        for (Object[] e : execCalls) {
            Address at = (Address) e[0];
            String bare = (String) e[1];
            PcodeOpAST op = (PcodeOpAST) e[2];
            Varnode arg0 = op.getNumInputs() > 1 ? op.getInput(1) : null;

            Set<String> direct = new LinkedHashSet<>();
            collectParams(arg0, walkDepth, direct);

            Loc via = locOf(arg0, walkDepth);
            // Only a write that happens *before* this call can have filled the
            // buffer. Dropping the ordering test would let a later, unrelated
            // write into the same stack slot manufacture a finding.
            String indirect = null;
            if (via != null && tainted.containsKey(via)
                    && taintedAt.get(via).compareTo(at) < 0) {
                indirect = tainted.get(via);
            }

            if (direct.isEmpty() && indirect == null) {
                continue;
            }
            Finding f = new Finding();
            f.rule = "R2";
            f.sink = bare;
            f.site = at.toString();
            f.function = fn.getName();
            f.entry = fn.getEntryPoint().toString();
            f.parameter = direct.isEmpty() ? indirect : String.join(",", direct);
            f.detail = direct.isEmpty()
                ? "argument is " + via + ", which a request parameter was written into "
                  + "earlier in this function"
                : "request parameter reaches the command argument directly";
            findings.add(f);
        }
    }

    // ------------------------------------------------------------ provenance

    /** Names of request parameters reachable backwards from this varnode. */
    private void collectParams(Varnode vn, int depth, Set<String> out) {
        if (vn == null || depth <= 0 || out.size() > 8) {
            return;
        }
        PcodeOp def = vn.getDef();
        if (def == null) {
            return;
        }
        if (def.getOpcode() == PcodeOp.CALL || def.getOpcode() == PcodeOp.CALLIND) {
            if (isAccessor(def)) {
                String name = firstLiteralArg(def);
                if (name != null && !name.isEmpty()) {
                    out.add(name);
                    return;
                }
            }
        }
        for (int i = 0; i < def.getNumInputs(); i++) {
            collectParams(def.getInput(i), depth - 1, out);
        }
    }

    /**
     * Resolve a varnode to a stack slot or a global address, so two references
     * to the same buffer compare equal. Anything else is null, and null means
     * "not matched" rather than "safe" -- which is why the count is a floor.
     */
    private Loc locOf(Varnode vn, int depth) {
        if (vn == null || depth <= 0) {
            return null;
        }
        if (vn.getHigh() != null && vn.getHigh().getSymbol() != null
                && vn.getHigh().getSymbol().getStorage() != null
                && vn.getHigh().getSymbol().getStorage().isStackStorage()) {
            return new Loc("stack", vn.getHigh().getSymbol().getStorage().getStackOffset());
        }
        if (vn.isConstant()) {
            Address a = toAddrSafe(vn.getOffset());
            return a != null ? new Loc("global", vn.getOffset()) : null;
        }
        PcodeOp def = vn.getDef();
        if (def == null) {
            return null;
        }
        switch (def.getOpcode()) {
            case PcodeOp.COPY:
            case PcodeOp.CAST:
            case PcodeOp.INDIRECT:
            case PcodeOp.MULTIEQUAL:
                return locOf(def.getInput(0), depth - 1);
            case PcodeOp.PTRSUB:
            case PcodeOp.PTRADD:
            case PcodeOp.INT_ADD: {
                Varnode a = def.getInput(0);
                Varnode b = def.getInput(1);
                // sp + const  -> a stack location. Sign-extended: a frame offset
                // is negative and getOffset() is unsigned, so without this the
                // report reads "sp+4294966852" for what is sp-444.
                if (a != null && b != null && b.isConstant() && isStackPointer(a)) {
                    return new Loc("stack", (int) b.getOffset());
                }
                if (a != null && a.isConstant() && b != null && b.isConstant()) {
                    return new Loc("global", a.getOffset() + b.getOffset());
                }
                Loc l = locOf(a, depth - 1);
                return l != null ? l : locOf(b, depth - 1);
            }
            default:
                return null;
        }
    }

    private boolean isStackPointer(Varnode vn) {
        if (vn == null) {
            return false;
        }
        var reg = currentProgram.getRegister(vn.getAddress());
        return reg != null && ("sp".equalsIgnoreCase(reg.getName())
                               || "s8".equalsIgnoreCase(reg.getName()));
    }

    /**
     * Size of the named global at this address.
     *
     * Ghidra's defined-data length is not it: `lastUrl` is typed as a single
     * undefined byte and reports 1, when the symbol table says 100. W04's whole
     * `lastUrl[100]` finding rests on the size being right, so the distance to
     * the next symbol is used as the bound and the defined-data length only as a
     * fallback. Both are conservative in the same direction -- they can be too
     * small, never too large.
     */
    private int globalSize(long addr) {
        try {
            Address a = toAddrSafe(addr);
            if (a == null) {
                return -1;
            }
            var st = currentProgram.getSymbolTable();
            if (st.getPrimarySymbol(a) == null) {
                return -1;
            }
            var next = st.getSymbolIterator(a.add(1), true);
            while (next.hasNext()) {
                var s = next.next();
                if (s.getAddress().getAddressSpace().equals(a.getAddressSpace())
                        && s.getAddress().compareTo(a) > 0) {
                    long d = s.getAddress().subtract(a);
                    if (d > 0 && d < 0x10000) {
                        return (int) d;
                    }
                    break;
                }
            }
            var data = currentProgram.getListing().getDefinedDataAt(a);
            return data != null ? data.getLength() : -1;
        } catch (Exception e) {
            return -1;
        }
    }

    private String symbolAt(long addr) {
        try {
            Address a = toAddrSafe(addr);
            if (a == null) {
                return "";
            }
            var sym = currentProgram.getSymbolTable().getPrimarySymbol(a);
            return sym == null ? "" : sym.getName();
        } catch (Exception e) {
            return "";
        }
    }

    /** The CALL op the decompiler produced for the instruction at {@code at}. */
    private PcodeOpAST callOpAt(HighFunction hf, Address at) {
        var ops = hf.getPcodeOps(at);
        while (ops != null && ops.hasNext()) {
            PcodeOpAST op = (PcodeOpAST) ops.next();
            if (op.getOpcode() == PcodeOp.CALL || op.getOpcode() == PcodeOp.CALLIND) {
                return op;
            }
        }
        return null;
    }

    private Address targetOf(PcodeOp call) {
        Varnode t = call.getInput(0);
        if (t == null) {
            return null;
        }
        if (t.isAddress()) {
            return t.getAddress();
        }
        return t.isConstant() ? toAddrSafe(t.getOffset()) : null;
    }

    private boolean isAccessor(PcodeOp call) {
        Address t = targetOf(call);
        boolean hit = t != null && accessorTargets.contains(t);
        if (!hit) {
            String callee = calleeName(call);
            String n = bareName(callee).toLowerCase();
            hit = n.contains("get_cstream_var") || n.contains("getvar")
               || n.contains("boa_getvar") || n.contains("req_get");
        }
        if (hit) {
            accessorMatches++;
        }
        return hit;
    }

    /**
     * The first argument that resolves to a string literal — the parameter name.
     *
     * Address resolution is delegated to {@link BoaArgTrace#constAddr}, not
     * re-implemented. The version that *was* re-implemented here tested only
     * `isConstant()`, which on MIPS never holds for a lui/addiu-built string
     * address, so no parameter name was ever read and the gate reported a clean
     * V2.1.2. One resolver, one place to fix — the same conclusion W04 reached
     * about the PLT, arrived at again from the other end.
     */
    private String firstLiteralArg(PcodeOp call) {
        for (int i = 1; i < call.getNumInputs(); i++) {
            long v = BoaArgTrace.constAddr(call.getInput(i), 4);
            if (v < 0) {
                continue;
            }
            String s = stringAt(toAddrSafe(v));
            if (s != null && !s.isEmpty()) {
                return s;
            }
        }
        return null;
    }

    private String calleeName(PcodeOp call) {
        Varnode target = call.getInput(0);
        if (target == null) {
            return null;
        }
        Address a = target.isConstant() ? toAddrSafe(target.getOffset()) : target.getAddress();
        if (a == null) {
            return null;
        }
        Function f = getFunctionAt(a);
        if (f != null) {
            Function thunked = f.getThunkedFunction(true);
            return thunked != null ? thunked.getName() : f.getName();
        }
        var sym = currentProgram.getSymbolTable().getPrimarySymbol(a);
        return sym == null ? null : sym.getName();
    }

    private String bareName(String n) {
        if (n == null) {
            return "";
        }
        int i = n.lastIndexOf("::");
        String s = i >= 0 ? n.substring(i + 2) : n;
        return s.startsWith("_") ? s.substring(1) : s;
    }

    private boolean in(String needle, String[] hay) {
        for (String h : hay) {
            if (h.equals(needle)) {
                return true;
            }
        }
        return false;
    }

    private Address toAddrSafe(long v) {
        try {
            Address a = toAddr(v);
            return currentProgram.getMemory().contains(a) ? a : null;
        } catch (Exception e) {
            return null;
        }
    }

    private String stringAt(Address a) {
        if (a == null) {
            return null;
        }
        try {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 64; i++) {
                int c = getByte(a.add(i)) & 0xFF;
                if (c == 0) {
                    break;
                }
                if (c < 0x20 || c > 0x7E) {
                    return null;
                }
                sb.append((char) c);
            }
            return sb.length() >= 2 ? sb.toString() : null;
        } catch (Exception e) {
            return null;
        }
    }

    // ----------------------------------------------------------------- json

    private void writeJson(String outPath, String sha, List<Finding> findings,
                           int scanned, int failed) throws Exception {
        Map<String, Integer> byRule = new LinkedHashMap<>();
        byRule.put("R1", 0);
        byRule.put("R2", 0);
        byRule.put("R3", 0);
        for (Finding f : findings) {
            byRule.merge(f.rule, 1, Integer::sum);
        }

        boolean controlDeclared = controlMinimum >= 0;
        boolean controlPassed = !controlDeclared || findings.size() >= controlMinimum;
        boolean noAccessor = accessorMatches == 0;

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaGate\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sha));
            out.printf("  \"language\": \"%s\",%n",
                       esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"functions_scanned\": %d,%n", scanned);
            out.printf("  \"functions_not_decompiled\": %d,%n", failed);
            out.printf("  \"sink_call_sites\": %d,%n", callSites);
            out.printf("  \"accessor_calls_matched\": %d,%n", accessorMatches);
            out.printf("  \"sinks_not_resolved\": [%s],%n", quoteJoin(unresolvedSinks));
            out.printf("  \"walk_depth\": %d,%n", walkDepth);
            out.println("  \"rules\": {");
            out.println("    \"R1\": \"request parameter -> strcpy/strcat/sprintf, unbounded\",");
            out.println("    \"R2\": \"request parameter -> system/popen, directly or via a "
                        + "buffer written in the same function\",");
            out.println("    \"R3\": \"request parameter -> fixed-size global object\"");
            out.println("  },");
            out.printf("  \"findings_by_rule\": {\"R1\": %d, \"R2\": %d, \"R3\": %d},%n",
                       byRule.get("R1"), byRule.get("R2"), byRule.get("R3"));
            out.printf("  \"finding_count\": %d,%n", findings.size());
            out.printf("  \"control_minimum\": %d,%n", controlMinimum);
            out.printf("  \"control_passed\": %b,%n", controlPassed);
            out.printf("  \"would_pass_ci\": %b,%n", findings.isEmpty());

            // Three ways this gate can be wrong, all of them stated. The first
            // is the one that matters: a rule that has never fired on a build
            // known to be defective is a decoration, not a check.
            out.printf("  \"self_check\": {\"no_accessor_identified\": %b,"
                       + "\"control_declared\": %b,\"control_passed\": %b,"
                       + "\"decompile_failures\": %d,\"verdict\": \"%s\"},%n",
                       noAccessor, controlDeclared, controlPassed, failed,
                       noAccessor
                           ? "BROKEN - no call was recognised as the request-parameter "
                             + "accessor, so every rule here is vacuous. A stripped build "
                             + "needs accessor:<FUN_xxxxxxxx>."
                       : (controlDeclared && !controlPassed)
                           ? "BROKEN - the positive control demanded at least "
                             + controlMinimum + " findings on a build known to be defective "
                             + "and this run produced " + findings.size()
                             + ". The gate is wrong, not the build."
                       : "usable");

            out.println("  \"findings\": [");
            List<String> rows = new ArrayList<>();
            for (Finding f : findings) {
                rows.add(String.format(
                    "    {\"rule\":\"%s\",\"sink\":\"%s\",\"site\":\"%s\",\"function\":\"%s\","
                    + "\"entry\":\"%s\",\"parameter\":\"%s\",\"dest_size\":%d,\"detail\":\"%s\"}",
                    f.rule, esc(f.sink), f.site, esc(f.function), f.entry,
                    esc(f.parameter == null ? "" : f.parameter), f.destSize, esc(f.detail)));
            }
            out.println(String.join(",\n", rows));
            out.println("  ]");
            out.println("}");
        }
    }

    private String quoteJoin(java.util.Collection<String> items) {
        List<String> q = new ArrayList<>();
        for (String s : items) {
            q.add("\"" + esc(s) + "\"");
        }
        return String.join(",", q);
    }

    private String esc(String s) {
        if (s == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder(s.length() + 8);
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"':  sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n");  break;
                case '\r': sb.append("\\r");  break;
                case '\t': sb.append("\\t");  break;
                default:
                    if (c < 0x20 || c > 0x7E) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        return sb.toString();
    }
}
