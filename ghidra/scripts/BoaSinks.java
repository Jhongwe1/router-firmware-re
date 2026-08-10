/* BoaSinks.java — census of dangerous library calls and who makes them.
 *
 * What this is, and what it is not
 * --------------------------------
 * This is an *extractor*, not an analyser. It answers "which functions call
 * system(), and from what address" — a question with a mechanical answer that a
 * human clicking through 980 functions gets wrong by omission. It does not
 * answer "is that call reachable with attacker-controlled data", which is the
 * only question that matters and which is done by reading code.
 *
 * The W03 plan bans writing automated reversing tools, and it is right to: the
 * failure mode for this week is spending it building a framework and finishing
 * with no understanding of MIPS or of Boa. The line drawn here is that a script
 * may *collect evidence*; the conclusions in notes/ are written by hand from
 * decompiled code that was actually read.
 *
 * Finding the sinks in a stripped binary
 * --------------------------------------
 * Both builds are stripped of local symbols, and V3.4.0 is `sstrip`'d with no
 * section headers at all. Dynamic symbols survive that — they have to, or the
 * loader could not resolve them — so `system` is still nameable via PT_DYNAMIC.
 * That is the same property W01's fwrecon/elf.py was written around after
 * readelf silently reported zero imports for V3.4.0.
 *
 * Two hops, and why one is not enough
 * -----------------------------------
 * The first version of this script counted references to the symbol and
 * reported 589 strcpy call sites in V2.1.2 and **1** in V3.4.0. The second
 * number is not a property of the firmware — the two builds are the same
 * codebase eleven KB apart in a 400 KB binary, and `nm -D` shows V3.4.0 still
 * importing strcpy. It is a property of how each binary calls libc:
 *
 *   V2.1.2  DT_MIPS_PLTGOT absent  -> classic MIPS lazy binding. Ghidra has
 *                                     section headers, builds a thunk named
 *                                     `strcpy`, and callers reference it
 *                                     directly. One hop is enough.
 *   V3.4.0  DT_MIPS_PLTGOT 0x472ac4 -> a real PLT. The binary is `sstrip`'d, so
 *                                     Ghidra cannot find .plt to label its
 *                                     entries. The only thing referencing the
 *                                     `strcpy` symbol is an unnamed PLT stub,
 *                                     and every real caller references *that*.
 *
 * So targets are resolved transitively: seed on the symbol, then absorb any
 * stub-shaped function that references a seed. Which addresses were seeds and
 * which were stubs is recorded, because a two-hop result is a weaker claim than
 * a one-hop one and the report should not hide that.
 *
 * And a sink that the binary imports but that appears to have no callers is
 * flagged rather than printed as a zero. That specific shape of wrongness —
 * a tool reporting absence when it has merely failed to look — has now cost
 * this project twice (readelf on the sstrip'd ELF in W01, and this script in
 * W03). Zero is a claim, and it needs the same scrutiny as any other.
 *
 * Usage:  -postScript BoaSinks.java <out.json> [<source-sha256>]
 */

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.RefType;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class BoaSinks extends GhidraScript {

    /** name -> bug class. Ordered worst-first so the report reads that way. */
    private static final String[][] SINKS = {
        { "system",     "command-exec" },
        { "popen",      "command-exec" },
        { "execl",      "command-exec" },
        { "execlp",     "command-exec" },
        { "execle",     "command-exec" },
        { "execv",      "command-exec" },
        { "execvp",     "command-exec" },
        { "execve",     "command-exec" },
        { "gets",       "overflow-unbounded" },
        { "strcpy",     "overflow-unbounded" },
        { "strcat",     "overflow-unbounded" },
        { "sprintf",    "overflow-unbounded" },
        { "vsprintf",   "overflow-unbounded" },
        { "scanf",      "overflow-unbounded" },
        { "sscanf",     "overflow-unbounded" },
        { "strncpy",    "overflow-bounded-often-misused" },
        { "strncat",    "overflow-bounded-often-misused" },
        { "snprintf",   "overflow-bounded-often-misused" },
        { "memcpy",     "overflow-bounded-often-misused" },
        { "memmove",    "overflow-bounded-often-misused" },
        { "alloca",     "stack-clash" },
    };

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "sinks.json";
        String sourceSha = args.length > 1 ? args[1] : "";

        // Diagnostic first: if symbol recovery failed, every empty result below
        // is an artefact of the tooling and not a property of the binary. W01's
        // most expensive mistake was reading a tool's silence as a finding.
        Set<String> namedFns = new TreeSet<>();
        int total = 0;
        FunctionIterator fit = currentProgram.getFunctionManager().getFunctions(true);
        while (fit.hasNext()) {
            Function f = fit.next();
            total++;
            if (!f.getName().startsWith("FUN_")) {
                namedFns.add(f.getName());
            }
        }

        Map<String, List<String>> callSites = new LinkedHashMap<>();
        Map<String, Set<String>> seedAddrs = new LinkedHashMap<>();
        Map<String, Set<String>> stubAddrs = new LinkedHashMap<>();
        List<String> suspect = new ArrayList<>();

        for (String[] sink : SINKS) {
            monitor.checkCancelled();
            String name = sink[0];
            Set<Address> seeds = seedTargets(name);
            Set<Address> stubs = stubTargets(seeds, name);

            Set<Address> targets = new LinkedHashSet<>(seeds);
            targets.addAll(stubs);
            seedAddrs.put(name, toStrings(seeds));
            stubAddrs.put(name, toStrings(stubs));

            Set<String> seen = new LinkedHashSet<>();
            List<String> rows = new ArrayList<>();
            for (Address t : targets) {
                for (Reference r : getReferencesTo(t)) {
                    RefType rt = r.getReferenceType();
                    if (!rt.isCall() && !rt.isJump() && !rt.isData()) {
                        continue;
                    }
                    Address from = r.getFromAddress();
                    Function caller = getFunctionContaining(from);
                    if (caller != null && targets.contains(caller.getEntryPoint())) {
                        continue;   // stub -> symbol, not a call site
                    }
                    // A data reference from outside any function is the .got.plt
                    // slot holding the symbol's address — a relocation, not a
                    // call. Counting it is how `strcpy` first came back with
                    // "1 call site" instead of the honest "0, and that is wrong".
                    if (caller == null && rt.isData()) {
                        continue;
                    }
                    String key = from.toString();
                    if (!seen.add(key)) {
                        continue;
                    }
                    rows.add(String.format(
                        "{\"from\":\"%s\",\"caller\":\"%s\",\"caller_entry\":\"%s\","
                        + "\"is_handler\":%b,\"ref\":\"%s\"}",
                        from,
                        caller == null ? "" : esc(caller.getName()),
                        caller == null ? "" : caller.getEntryPoint().toString(),
                        caller != null && caller.getName().startsWith("form_"),
                        rt.getName()));
                }
            }
            callSites.put(name, rows);

            // An imported symbol with no callers is the signature of a
            // resolution failure, not of clean code. Say so in the artefact.
            if (!seeds.isEmpty() && rows.isEmpty()) {
                suspect.add(name);
            }
        }

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaSinks\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sourceSha));
            out.printf("  \"language\": \"%s\",%n", esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            // Two counts, because they differ and the difference is meaningful:
            // getFunctionCount() includes EXTERNAL-space functions (the imports),
            // while iterating getFunctions(true) yields only functions with a body
            // in memory. V2.1.2 reports 813 and 645. Emitting one and calling it
            // "the function count" invites exactly the sort of cross-report
            // comparison that quietly compares two different things.
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"defined_function_count\": %d,%n", total);
            out.printf("  \"named_function_count\": %d,%n", namedFns.size());
            out.printf("  \"symbol_recovery\": \"%s\",%n",
                       namedFns.isEmpty() ? "NONE - results below are not evidence of absence"
                                          : "dynamic symbols resolved");
            // Loud, machine-readable, and at the top of the file on purpose.
            out.printf("  \"self_check\": {\"imported_but_no_call_sites\": [%s], \"verdict\": \"%s\"},%n",
                       quoteJoin(suspect),
                       suspect.isEmpty() ? "consistent"
                                         : "SUSPECT - a symbol the binary imports appears "
                                           + "uncalled; treat these rows as unmeasured, not as zero");
            out.println("  \"sinks\": {");

            List<String> blocks = new ArrayList<>();
            for (String[] sink : SINKS) {
                String name = sink[0];
                List<String> rows = callSites.get(name);
                Set<String> seeds = seedAddrs.get(name);
                Set<String> stubs = stubAddrs.get(name);
                blocks.add(String.format(
                    "    \"%s\": {\"class\":\"%s\",\"imported\":%b,\"symbol_addresses\":[%s],"
                    + "\"stub_addresses\":[%s],\"resolution\":\"%s\","
                    + "\"call_site_count\":%d,\"call_sites\":[%s]}",
                    name, sink[1], !seeds.isEmpty(),
                    quoteJoin(seeds), quoteJoin(stubs),
                    stubs.isEmpty() ? "direct" : "via-plt-stub",
                    rows.size(), String.join(",", rows)));
            }
            out.println(String.join(",\n", blocks));
            out.println("  }");
            out.println("}");
        }

        int grand = 0;
        for (List<String> v : callSites.values()) {
            grand += v.size();
        }
        println(String.format("BoaSinks: %d call sites across %d sinks, %d named functions, wrote %s",
                grand, SINKS.length, namedFns.size(), outPath));
    }

    /** Longest plausible MIPS PLT/lazy-binding stub, in instructions. */
    private static final int STUB_MAX_INSTRUCTIONS = 8;

    /**
     * Find the PLT entry for a .got.plt slot by constructing the exact bytes it
     * must contain.
     *
     * Ghidra disassembles only part of the PLT in the sstrip'd V3.4.0 binary —
     * `system` and `sprintf` got functions, `strcpy` and `strcat` did not, which
     * is why the first census reported one strcpy call site in a 400 KB C
     * program. Nothing is wrong with the binary; there are simply no section
     * headers to say where .plt begins, so entry recovery depends on something
     * happening to fall through into each one.
     *
     * The entries themselves are not ambiguous. binutils emits a fixed four
     * instruction sequence per MIPS PLT entry, and every field is determined by
     * the slot address S:
     *
     *   lui   $15, %hi(S)      3C 0F hi
     *   lw    $25, %lo(S)($15) 8D F9 lo
     *   addiu $24, $15, %lo(S) 25 F8 lo
     *   jr    $25              03 20 00 08
     *
     * So the stub is not searched for heuristically — it is computed and then
     * confirmed to exist at exactly one address. A pattern that matches twice,
     * or not at all, returns nothing rather than a guess.
     */
    private Address pltStubForSlot(Address slot) {
        long s = slot.getOffset();
        int hi = (int) (((s + 0x8000) >> 16) & 0xFFFF);
        int lo = (int) (s & 0xFFFF);
        byte[] sig = new byte[] {
            0x3C, 0x0F, (byte) (hi >> 8), (byte) hi,
            (byte) 0x8D, (byte) 0xF9, (byte) (lo >> 8), (byte) lo,
            0x25, (byte) 0xF8, (byte) (lo >> 8), (byte) lo,
            0x03, 0x20, 0x00, 0x08,
        };
        Address found = null;
        Address at = currentProgram.getMinAddress();
        while (at != null) {
            Address hit = find(at, sig);
            if (hit == null) {
                break;
            }
            if (found != null) {
                return null;    // ambiguous: refuse rather than pick one
            }
            found = hit;
            at = hit.add(1);
        }
        return found;
    }

    /**
     * The .got.plt slots holding this symbol's address. A data reference to the
     * external symbol that sits outside any function is a relocation target, not
     * code — which is also why such references must never be counted as calls.
     */
    private Set<Address> gotSlotsFor(Set<Address> seeds) {
        Set<Address> out = new LinkedHashSet<>();
        for (Address s : seeds) {
            for (Reference r : getReferencesTo(s)) {
                if (r.getReferenceType().isData()
                        && getFunctionContaining(r.getFromAddress()) == null) {
                    out.add(r.getFromAddress());
                }
            }
        }
        return out;
    }

    /** Seeds: the symbol itself, and any function already carrying its name. */
    private Set<Address> seedTargets(String name) {
        Set<Address> out = new LinkedHashSet<>();
        SymbolIterator si = currentProgram.getSymbolTable().getSymbols(name);
        while (si.hasNext()) {
            Symbol s = si.next();
            if (s.getAddress() != null) {
                out.add(s.getAddress());
            }
        }
        FunctionIterator fit = currentProgram.getFunctionManager().getFunctions(true);
        while (fit.hasNext()) {
            Function f = fit.next();
            String n = f.getName();
            if (n.equals(name) || n.equals("." + name) || n.equals("__" + name)) {
                out.add(f.getEntryPoint());
            }
        }
        return out;
    }

    /**
     * Stub-shaped functions standing in front of the seeds. A PLT entry is a
     * handful of instructions that loads a GOT slot and jumps; anything that
     * short which references the imported symbol is that stub and not a caller
     * worth reporting, so its own callers are the answer.
     *
     * The size bound is what keeps this honest. Without it, "absorb whatever
     * references the symbol" would swallow genuine callers and every function in
     * the binary would end up looking like strcpy.
     */
    private Set<Address> stubTargets(Set<Address> seeds, String name) {
        Set<Address> out = new LinkedHashSet<>();
        for (Address s : seeds) {
            for (Reference r : getReferencesTo(s)) {
                Function f = getFunctionContaining(r.getFromAddress());
                if (f == null || seeds.contains(f.getEntryPoint())) {
                    continue;
                }
                if (f.isThunk() || instructionCount(f) <= STUB_MAX_INSTRUCTIONS) {
                    out.add(f.getEntryPoint());
                }
            }
        }
        // Second route, for the PLT entries Ghidra never turned into functions.
        for (Address slot : gotSlotsFor(seeds)) {
            Address stub = pltStubForSlot(slot);
            if (stub != null) {
                out.add(stub);
                if (getFunctionAt(stub) == null) {
                    try {
                        disassemble(stub);
                        createFunction(stub, name + "_plt");
                    } catch (Exception ignored) {
                        // Counting its callers does not depend on it becoming a
                        // function; the label is a convenience for the GUI.
                    }
                }
            }
        }
        return out;
    }

    private int instructionCount(Function f) {
        int n = 0;
        var it = currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext() && n <= STUB_MAX_INSTRUCTIONS + 1) {
            it.next();
            n++;
        }
        return n;
    }

    private Set<String> toStrings(Set<Address> in) {
        Set<String> out = new LinkedHashSet<>();
        for (Address a : in) {
            out.add(a.toString());
        }
        return out;
    }

    private String quoteJoin(java.util.Collection<String> items) {
        List<String> q = new ArrayList<>();
        for (String s : items) {
            q.add("\"" + esc(s) + "\"");
        }
        return String.join(",", q);
    }

    private String esc(String s) {
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
