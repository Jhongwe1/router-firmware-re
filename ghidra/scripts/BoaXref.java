/* BoaXref.java — who calls this, what does it call, and can a request reach it.
 *
 * Why this exists
 * ---------------
 * W03 ended with a sentence that should not appear in an analysis:
 *
 *   "the selector used for it returned nothing, which is a tooling result and
 *    not an answer"                                    — notes/auth-flow.md
 *
 * `BoaDecompile`'s `callers:` selector looks a symbol up by name. Ghidra does
 * not index default names — `FUN_0040b850` is a *generated* label, not a symbol
 * in the name table — so asking for the callers of an unnamed function returned
 * an empty list that was indistinguishable from "nothing calls it". In the
 * V3.4.0 build almost every function is unnamed, which is precisely where the
 * question mattered.
 *
 * This script answers the same question from the listing instead of the symbol
 * table, and refuses to be silent: a selector that resolves to nothing is
 * reported by name in `unresolved_selectors`, and the file's `self_check`
 * verdict goes to SUSPECT. An empty answer and a failed question look different
 * in the output, which is the entire point.
 *
 * Reachability
 * ------------
 * `notes/sink-inventory.md` ranks findings by *reachability × control × absence
 * of a check*, and reachability was being argued by hand. With `depth:N` this
 * walks the call graph backwards N levels and reports, per function, every
 * ancestor and whether any of them is a `/boafrm/` handler — the names
 * BoaFormTable persisted into the program database as `form_*`. That converts
 * "this looks reachable from the web" into an enumerated path, or into the
 * honest statement that no path was found within N hops.
 *
 * Two things it deliberately does not do
 * --------------------------------------
 *   - It does not follow indirect calls. MIPS `jalr t9` through a table is how
 *     handleForm reaches every handler, and Ghidra cannot resolve those without
 *     help; the tables that matter were recovered structurally by BoaFormTable
 *     instead, and the roots recorded here are honest about stopping.
 *   - It does not decide anything. It emits edges. Whether a path is
 *     *traversable with attacker data* is read by hand from BoaArgTrace output.
 *
 * Usage:
 *   -postScript BoaXref.java <out.json> <sha256|-> <selector> [<selector>...]
 *
 * Selectors:  name:handleForm  @0040b850  prefix:form_  string:AUTHG_IP_ADDR
 *             callers:system   refs:0048e9e8   depth:N (option, not a selector)
 *
 * `refs:` is the one that answers questions about *globals* rather than
 * functions — "who writes this flag, and who reads it back". It emits a
 * separate `data_xrefs` block carrying the read/write direction, because for an
 * authorisation flag the direction is the whole question.
 */

import java.io.PrintWriter;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.RefType;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class BoaXref extends GhidraScript {

    /** A stub this short in front of an imported symbol is a PLT entry. */
    private static final int STUB_MAX_INSTRUCTIONS = 8;

    /** Default reverse-reachability depth. 0 disables the walk entirely. */
    private int depth = 0;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            println("BoaXref: need <out.json> <sha256|-> <selector>...");
            return;
        }
        String outPath = args[0];
        String sha = "-".equals(args[1]) ? "" : args[1];

        Map<Function, String> selected = new LinkedHashMap<>();
        List<String> unresolved = new ArrayList<>();
        List<String> dataXrefs = new ArrayList<>();
        for (int i = 2; i < args.length; i++) {
            String sel = args[i];
            if (sel.startsWith("depth:")) {
                depth = Integer.parseInt(sel.substring(6));
                continue;
            }
            if (sel.startsWith("refs:")) {
                List<String> rows = dataXrefsFor(toAddr(sel.substring(5)), sel);
                if (rows.isEmpty()) {
                    unresolved.add(sel);
                } else {
                    dataXrefs.addAll(rows);
                }
                continue;
            }
            List<Function> hits = resolve(sel);
            if (hits.isEmpty()) {
                unresolved.add(sel);
                continue;
            }
            for (Function f : hits) {
                selected.putIfAbsent(f, sel);
            }
        }

        List<String> blocks = new ArrayList<>();
        for (var kv : selected.entrySet()) {
            monitor.checkCancelled();
            blocks.add(describe(kv.getKey(), kv.getValue()));
        }

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaXref\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sha));
            out.printf("  \"language\": \"%s\",%n",
                       esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"reverse_depth\": %d,%n", depth);
            // A question that failed to parse must not look like a question that
            // was answered "no". This is the whole reason the script exists.
            out.printf("  \"self_check\": {\"unresolved_selectors\": [%s], \"verdict\": \"%s\"},%n",
                       quoteJoin(unresolved),
                       unresolved.isEmpty()
                           ? "consistent"
                           : "SUSPECT - a selector matched no function; that is a tooling "
                             + "result, not a finding about the binary");
            out.println("  \"data_xrefs\": [");
            out.println(String.join(",\n", dataXrefs));
            out.println("  ],");
            out.println("  \"functions\": [");
            out.println(String.join(",\n", blocks));
            out.println("  ]");
            out.println("}");
        }
        println(String.format("BoaXref: %d functions, %d data xrefs, %d unresolved selectors, wrote %s",
                              selected.size(), dataXrefs.size(), unresolved.size(), outPath));
    }

    /**
     * Every reference to one address, with its direction.
     *
     * Ghidra's RefType already knows read from write; surfacing it is what turns
     * "this global is touched in four places" into "written in three, read in
     * one, and the read is the one that decides". `access` is reported verbatim
     * rather than reduced to a boolean, so a reference Ghidra could not classify
     * shows up as such instead of defaulting to one of the two answers.
     */
    private List<String> dataXrefsFor(Address target, String selector) {
        List<String> rows = new ArrayList<>();
        for (Reference r : getReferencesTo(target)) {
            Function c = getFunctionContaining(r.getFromAddress());
            RefType rt = r.getReferenceType();
            String access = rt.isWrite() ? "write" : rt.isRead() ? "read" : rt.getName();
            Instruction ins = getInstructionAt(r.getFromAddress());
            rows.add(String.format(
                "    {\"selector\":\"%s\",\"target\":\"%s\",\"site\":\"%s\",\"access\":\"%s\","
                + "\"in\":\"%s\",\"in_entry\":\"%s\",\"insn\":\"%s\"}",
                esc(selector), target, r.getFromAddress(), esc(access),
                c == null ? "" : esc(c.getName()),
                c == null ? "" : c.getEntryPoint().toString(),
                ins == null ? "" : esc(ins.toString())));
        }
        return rows;
    }

    // ---------------------------------------------------------------- describe

    private String describe(Function f, String selector) throws Exception {
        List<String> callers = new ArrayList<>();
        for (Reference r : getReferencesTo(f.getEntryPoint())) {
            if (!r.getReferenceType().isCall() && !r.getReferenceType().isJump()) {
                continue;
            }
            Function c = getFunctionContaining(r.getFromAddress());
            callers.add(String.format(
                "{\"site\":\"%s\",\"caller\":\"%s\",\"caller_entry\":\"%s\",\"ref\":\"%s\"}",
                r.getFromAddress(),
                c == null ? "" : esc(c.getName()),
                c == null ? "" : c.getEntryPoint().toString(),
                r.getReferenceType().getName()));
        }

        List<String> callees = new ArrayList<>();
        List<String> strings = new ArrayList<>();
        Set<String> seenStr = new LinkedHashSet<>();
        InstructionIterator it =
            currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            for (Reference r : ins.getReferencesFrom()) {
                Address t = r.getToAddress();
                if (t == null) {
                    continue;
                }
                RefType rt = r.getReferenceType();
                if (rt.isCall()) {
                    callees.add(String.format(
                        "{\"site\":\"%s\",\"target\":\"%s\",\"target_entry\":\"%s\"}",
                        ins.getAddress(), esc(resolveName(t)), t));
                } else {
                    String s = stringAt(t);
                    if (s != null && seenStr.add(s)) {
                        strings.add(String.format("{\"at\":\"%s\",\"site\":\"%s\",\"text\":\"%s\"}",
                                                  t, ins.getAddress(), esc(s)));
                    }
                }
            }
        }

        String reach = depth > 0 ? reverseReach(f) : "null";

        return String.format(
            "    {\"function\":\"%s\",\"entry\":\"%s\",\"size\":%d,\"selector\":\"%s\","
            + "\"caller_count\":%d,\"callers\":[%s],"
            + "\"callee_count\":%d,\"callees\":[%s],"
            + "\"strings\":[%s],\"reachability\":%s}",
            esc(f.getName()), f.getEntryPoint(), f.getBody().getNumAddresses(), esc(selector),
            callers.size(), String.join(",", callers),
            callees.size(), String.join(",", callees),
            String.join(",", strings),
            reach);
    }

    /**
     * Walk callers breadth-first up to `depth` hops.
     *
     * Reported: every ancestor found, the ones that are `/boafrm/` handlers
     * (BoaFormTable names those `form_*` in the program database), and whether
     * the walk was cut short by the depth limit. The last flag matters — a
     * result of "no handler reaches this" is only meaningful if the frontier was
     * exhausted, and it usually is not.
     */
    private String reverseReach(Function f) throws Exception {
        Set<String> seen = new LinkedHashSet<>();
        Set<String> handlers = new LinkedHashSet<>();
        List<String> roots = new ArrayList<>();
        Deque<Object[]> queue = new ArrayDeque<>();
        queue.add(new Object[] { f, 0 });
        seen.add(f.getEntryPoint().toString());
        boolean truncated = false;

        while (!queue.isEmpty()) {
            monitor.checkCancelled();
            Object[] cur = queue.poll();
            Function fn = (Function) cur[0];
            int d = (Integer) cur[1];

            boolean any = false;
            for (Reference r : getReferencesTo(fn.getEntryPoint())) {
                if (!r.getReferenceType().isCall() && !r.getReferenceType().isJump()) {
                    continue;
                }
                Function c = getFunctionContaining(r.getFromAddress());
                if (c == null || c.equals(fn)) {
                    continue;
                }
                any = true;
                if (d + 1 > depth) {
                    truncated = true;
                    continue;
                }
                if (!seen.add(c.getEntryPoint().toString())) {
                    continue;
                }
                if (c.getName().startsWith("form_")) {
                    handlers.add(c.getName() + "@" + c.getEntryPoint());
                }
                queue.add(new Object[] { c, d + 1 });
            }
            // No callers at all: either a dispatch-table target reached only
            // through `jalr`, or genuinely dead. The distinction is not
            // decidable here, so the address is reported and not judged.
            if (!any && d > 0) {
                roots.add(fn.getName() + "@" + fn.getEntryPoint());
            }
        }

        return String.format(
            "{\"depth\":%d,\"ancestors\":%d,\"handlers\":[%s],\"indirect_or_dead_roots\":[%s],"
            + "\"truncated\":%b,\"note\":\"%s\"}",
            depth, seen.size() - 1, quoteJoin(handlers), quoteJoin(roots), truncated,
            truncated
                ? "frontier hit the depth limit; absence of a handler here is not proof of one"
                : "frontier exhausted within the depth limit");
    }

    // ---------------------------------------------------------------- helpers

    /**
     * Name a call target, seeing through the PLT.
     *
     * In the sstrip'd V3.4.0 build a call to `strcpy` lands on an unnamed
     * four-instruction stub, so a raw callee list reads as a wall of
     * `FUN_004xxxxx`. If the target is short enough to be a stub and references
     * exactly one external symbol, that symbol's name is the useful answer —
     * marked with a `@plt` suffix so a reader can tell a resolved stub from a
     * function that carried its own symbol.
     */
    private String resolveName(Address target) {
        Function f = getFunctionAt(target);
        if (f == null) {
            Symbol s = getSymbolAt(target);
            return s != null ? s.getName() : ("?@" + target);
        }
        if (!f.getName().startsWith("FUN_")) {
            return f.getName();
        }
        if (instructionCount(f) <= STUB_MAX_INSTRUCTIONS) {
            String only = null;
            InstructionIterator it =
                currentProgram.getListing().getInstructions(f.getBody(), true);
            while (it.hasNext()) {
                for (Reference r : it.next().getReferencesFrom()) {
                    Symbol s = getSymbolAt(r.getToAddress());
                    if (s == null || s.getName().startsWith("FUN_")
                            || s.getName().startsWith("DAT_")
                            || s.getName().startsWith("PTR_")
                            || s.getName().startsWith("LAB_")) {
                        continue;
                    }
                    if (only != null && !only.equals(s.getName())) {
                        return f.getName();     // ambiguous: do not guess
                    }
                    only = s.getName();
                }
            }
            if (only != null) {
                return only + "@plt";
            }
        }
        return f.getName();
    }

    private int instructionCount(Function f) {
        int n = 0;
        InstructionIterator it =
            currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext() && n <= STUB_MAX_INSTRUCTIONS + 1) {
            it.next();
            n++;
        }
        return n;
    }

    private List<Function> resolve(String selector) {
        List<Function> out = new ArrayList<>();
        if (selector.startsWith("prefix:")) {
            String p = selector.substring(7);
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext()) {
                Function f = it.next();
                if (f.getName().startsWith(p)) {
                    out.add(f);
                }
            }
        } else if (selector.startsWith("name:")) {
            String n = selector.substring(5);
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext()) {
                Function f = it.next();
                if (f.getName().equals(n)) {
                    out.add(f);
                }
            }
        } else if (selector.startsWith("@")) {
            Function f = getFunctionContaining(toAddr(selector.substring(1)));
            if (f != null) {
                out.add(f);
            }
        } else if (selector.startsWith("string:")) {
            for (Function f : functionsReferencingText(selector.substring(7))) {
                if (!out.contains(f)) {
                    out.add(f);
                }
            }
        } else if (selector.startsWith("callers:")) {
            String n = selector.substring(8);
            List<Address> targets = new ArrayList<>();
            SymbolIterator si = currentProgram.getSymbolTable().getSymbols(n);
            while (si.hasNext()) {
                Symbol s = si.next();
                if (s.getAddress() != null) {
                    targets.add(s.getAddress());
                }
            }
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext()) {
                Function f = it.next();
                if (f.getName().equals(n) || f.getName().equals("." + n)) {
                    targets.add(f.getEntryPoint());
                }
            }
            for (Address t : targets) {
                for (Reference r : getReferencesTo(t)) {
                    Function c = getFunctionContaining(r.getFromAddress());
                    if (c != null && !c.getName().equals(n) && !out.contains(c)) {
                        out.add(c);
                    }
                }
            }
        }
        return out;
    }

    private List<Function> functionsReferencingText(String needle) {
        List<Function> out = new ArrayList<>();
        try {
            Address at = currentProgram.getMinAddress();
            while (at != null) {
                Address hit = find(at, needle.getBytes("US-ASCII"));
                if (hit == null) {
                    break;
                }
                for (Reference r : getReferencesTo(hit)) {
                    Function c = getFunctionContaining(r.getFromAddress());
                    if (c != null && !out.contains(c)) {
                        out.add(c);
                    }
                }
                at = hit.add(1);
            }
        } catch (Exception ignored) {
            // Caller sees an empty list, which lands in unresolved_selectors.
        }
        return out;
    }

    private String stringAt(Address a) {
        try {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 160; i++) {
                int c = getByte(a.add(i)) & 0xFF;
                if (c == 0) {
                    break;
                }
                if (c != '\t' && c != '\n' && c != '\r' && (c < 0x20 || c > 0x7E)) {
                    return null;
                }
                sb.append((char) c);
            }
            return sb.length() >= 4 ? sb.toString() : null;
        } catch (Exception e) {
            return null;
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
