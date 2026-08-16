/* BoaArgTrace.java — what actually arrives at a dangerous call, per argument.
 *
 * The question this exists to answer
 * ---------------------------------
 * `BoaSinks` says *where* system() and strcpy() are called from. That is a list
 * of addresses, and W03 turned it into findings by decompiling handlers and
 * reading them one at a time. That does not scale past the handful that were
 * read, and "read 47 handlers by eye" is exactly how a real bug gets missed.
 *
 * The missing step is provenance: for each argument of each call, is it a string
 * literal, a stack buffer, or a value that came out of the request? This walks
 * the decompiler's SSA form backwards from the call and answers that
 * mechanically.
 *
 * The one pattern worth naming
 * ----------------------------
 * Realtek's Boa reads request parameters through one accessor:
 *
 *     req_get_cstream_var(req, "localPin", "")
 *
 * so a `CALL` whose own first string argument is a parameter name is the
 * boundary between attacker data and program data. When a backward walk lands on
 * one, this reports `request-parameter:localPin`, and the chain from there to
 * `system()` is the finding. Everything else it reports as what it is.
 *
 * Stack buffers get their size, not just their name
 * ------------------------------------------------
 * An overflow claim needs a number. When an argument resolves to a stack slot,
 * the frame size and the offset are emitted, plus the distance from that slot to
 * the top of the frame — which is the bound on how far a copy into it can run
 * before it reaches the saved return address. That is the difference between
 * "unbounded sprintf into a stack buffer" and "72 bytes of slack, then the
 * return address".
 *
 * What it will not tell you
 * -------------------------
 *   - Reachability. A call inside a handler is not automatically reachable with
 *     attacker data; the auth gate decides that, and it is read by hand in
 *     notes/auth-flow.md.
 *   - Whether a filter between the accessor and the sink is *sufficient*. It
 *     reports that a value passed through `FUN_00412345` and stops. Reading that
 *     function is the analyst's job.
 *   - Anything at all when the decompiler fails. Those call sites are emitted
 *     with `"status":"decompile-failed"` rather than dropped, because a sink
 *     that silently vanishes from a census is how the W03 strcpy count came back
 *     as 1.
 *
 * Usage:
 *   -postScript BoaArgTrace.java <out.json> <sha256|-> <spec> [<spec>...]
 *
 * Specs:
 *   sink:system            trace every call to system  (PLT-aware)
 *   in:form_               restrict to functions whose name starts with form_
 *   param:localPin         restrict to calls whose trace mentions this parameter
 *   accessor:FUN_004115a4  name the request-parameter accessor in a stripped
 *                          build, where the V2.1.2 symbol has no counterpart
 *   depth:6                backward-walk limit (default 6)
 */

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Iterator;
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
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class BoaArgTrace extends GhidraScript {

    private static final int STUB_MAX_INSTRUCTIONS = 8;
    private static final int TIMEOUT_SECONDS = 120;

    private int walkDepth = 6;
    private DecompInterface decomp;

    /** Accessor calls whose parameter name the resolver could not read. */
    private int accessorUnresolved = 0;

    /**
     * *Which* rows those are. Counting them was not enough: a report that says
     * "3 rows are unmeasured" without naming them cannot be acted on, so in
     * practice it gets read as a rounding error and skipped. W04-2 hit exactly
     * that on the 2018 build — verdict SUSPECT, three anonymous rows, nothing
     * to go and look at. The failure mode this project keeps meeting is not the
     * absent check, it is the check whose output nobody can use.
     */
    private final List<String> accessorUnresolvedSites = new ArrayList<>();

    /** Call site currently being described, so describe() can name its own failures. */
    private String currentSite = "";
    private String currentFunction = "";

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            println("BoaArgTrace: need <out.json> <sha256|-> <spec>...");
            return;
        }
        String outPath = args[0];
        String sha = "-".equals(args[1]) ? "" : args[1];

        List<String> sinkNames = new ArrayList<>();
        List<String> scopes = new ArrayList<>();
        List<String> paramFilter = new ArrayList<>();
        List<String> specArgs = new ArrayList<>();
        for (int i = 2; i < args.length; i++) {
            String s = args[i];
            specArgs.add(s);
            if (s.startsWith("sink:"))       { sinkNames.add(s.substring(5)); }
            else if (s.startsWith("in:"))    { scopes.add(s.substring(3)); }
            else if (s.startsWith("param:")) { paramFilter.add(s.substring(6)); }
            else if (s.startsWith("accessor:")) { accessorOverride = s.substring(9); }
            else if (s.startsWith("depth:")) { walkDepth = Integer.parseInt(s.substring(6)); }
        }

        decomp = new DecompInterface();
        decomp.setOptions(new DecompileOptions());
        if (!decomp.openProgram(currentProgram)) {
            throw new Exception("decompiler would not open the program: " + decomp.getLastMessage());
        }

        // sink name -> every address a call to it can land on (symbol + PLT stub)
        Map<String, Set<Address>> targets = new LinkedHashMap<>();
        List<String> unresolvedSinks = new ArrayList<>();
        for (String n : sinkNames) {
            Set<Address> t = resolveTargets(n);
            targets.put(n, t);
            if (t.isEmpty()) {
                unresolvedSinks.add(n);
            }
        }

        // Group call sites by the function containing them, so each function is
        // decompiled once however many sinks it calls.
        Map<Function, List<Object[]>> byFunction = new LinkedHashMap<>();
        int siteCount = 0;
        for (var kv : targets.entrySet()) {
            for (Address t : kv.getValue()) {
                for (Reference r : getReferencesTo(t)) {
                    if (!r.getReferenceType().isCall() && !r.getReferenceType().isJump()) {
                        continue;
                    }
                    Function caller = getFunctionContaining(r.getFromAddress());
                    if (caller == null || isStub(caller)) {
                        continue;
                    }
                    if (!inScope(caller, scopes)) {
                        continue;
                    }
                    byFunction.computeIfAbsent(caller, x -> new ArrayList<>())
                              .add(new Object[] { r.getFromAddress(), kv.getKey() });
                    siteCount++;
                }
            }
        }

        List<String> rows = new ArrayList<>();
        int failed = 0;
        try {
            for (var kv : byFunction.entrySet()) {
                monitor.checkCancelled();
                Function fn = kv.getKey();
                DecompileResults res = decomp.decompileFunction(fn, TIMEOUT_SECONDS, monitor);
                HighFunction hf = (res != null && res.decompileCompleted())
                                      ? res.getHighFunction() : null;
                int frameSize = fn.getStackFrame() == null ? 0 : fn.getStackFrame().getFrameSize();

                for (Object[] site : kv.getValue()) {
                    Address at = (Address) site[0];
                    String sink = (String) site[1];
                    if (hf == null) {
                        rows.add(String.format(
                            "    {\"sink\":\"%s\",\"site\":\"%s\",\"function\":\"%s\","
                            + "\"entry\":\"%s\",\"status\":\"decompile-failed\",\"args\":[]}",
                            sink, at, esc(fn.getName()), fn.getEntryPoint()));
                        failed++;
                        continue;
                    }
                    PcodeOpAST call = callOpAt(hf, at);
                    if (call == null) {
                        rows.add(String.format(
                            "    {\"sink\":\"%s\",\"site\":\"%s\",\"function\":\"%s\","
                            + "\"entry\":\"%s\",\"status\":\"no-call-op-in-ssa\",\"args\":[]}",
                            sink, at, esc(fn.getName()), fn.getEntryPoint()));
                        failed++;
                        continue;
                    }
                    List<String> argRows = new ArrayList<>();
                    Set<String> mentions = new LinkedHashSet<>();
                    currentSite = at.toString();
                    currentFunction = fn.getName();
                    for (int i = 1; i < call.getNumInputs(); i++) {
                        String d = describe(call.getInput(i), frameSize, walkDepth, mentions);
                        argRows.add(String.format("{\"n\":%d,%s}", i - 1, d));
                    }
                    if (!paramFilter.isEmpty()) {
                        boolean keep = false;
                        for (String p : paramFilter) {
                            if (mentions.contains(p)) {
                                keep = true;
                                break;
                            }
                        }
                        if (!keep) {
                            continue;
                        }
                    }
                    rows.add(String.format(
                        "    {\"sink\":\"%s\",\"site\":\"%s\",\"function\":\"%s\",\"entry\":\"%s\","
                        + "\"frame_size\":%d,\"status\":\"ok\",\"request_parameters\":[%s],"
                        + "\"args\":[%s]}",
                        sink, at, esc(fn.getName()), fn.getEntryPoint(), frameSize,
                        quoteJoin(mentions), String.join(",", argRows)));
                }
            }
        } finally {
            decomp.dispose();
        }

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaArgTrace\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sha));
            out.printf("  \"language\": \"%s\",%n",
                       esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"walk_depth\": %d,%n", walkDepth);
            // The specs that produced this report. Without them `call_sites_in_scope`
            // is a number with no denominator: W04 ran this with one set of sinks
            // and W04-2 with another, and the two counts (304 against 1508) read as
            // a finding about the firmware until you notice they answer different
            // questions. A report that cannot state its own question is not evidence,
            // which is the same rule that put source_sha256 in every report here.
            out.printf("  \"spec\": [%s],%n", quoteJoin(specArgs));
            out.printf("  \"call_sites_in_scope\": %d,%n", siteCount);
            out.printf("  \"traced\": %d,%n", rows.size());
            // A sink name that resolved to no address means the *question* failed,
            // and a call site the decompiler refused means the answer is missing
            // rather than empty. Both are stated, not swallowed.
            boolean deadOption = !accessorOverride.isEmpty() && !accessorOverrideMatched;
            // Computed program-wide, not over the scope: a sink the binary
            // imports that reaches nothing anywhere is a resolver failure. This
            // is the check that was missing when strcpy came back as 0 in the
            // sstrip'd build while the scope filter made it look like a
            // legitimate difference between the two firmware versions.
            List<String> noCallers = BoaPlt.importedWithNoCallers(this, sinkNames);
            // Zero accessor matches across the whole scope means no call site in
            // this report could ever have been attributed to a request
            // parameter. Every empty "request_parameters" is then a false
            // negative by construction, and saying so is the difference between
            // a clean report and a report about nothing.
            boolean noAccessorAtAll = accessorMatches == 0 && siteCount > 0;
            out.printf("  \"self_check\": {\"sinks_not_found\": [%s],\"untraced_sites\": %d,"
                       + "\"accessor_calls_with_unreadable_name\": %d,"
                       + "\"accessor_calls_with_unreadable_name_sites\": [%s],"
                       + "\"accessor_declared_but_never_matched\": %b,"
                       + "\"accessor_calls_matched\": %d,"
                       + "\"no_accessor_identified\": %b,"
                       + "\"imported_but_no_call_sites\": [%s],\"verdict\": \"%s\"},%n",
                       quoteJoin(unresolvedSinks), failed, accessorUnresolved,
                       String.join(",", accessorUnresolvedSites), deadOption,
                       accessorMatches, noAccessorAtAll,
                       quoteJoin(noCallers),
                       noAccessorAtAll
                           ? "SUSPECT - no call was recognised as the request-parameter accessor "
                             + "anywhere in scope, so every request_parameters field in this "
                             + "report is empty by construction and not by measurement. A "
                             + "stripped build needs accessor:<FUN_xxxxxxxx>."
                       : unresolvedSinks.isEmpty() && failed == 0 && accessorUnresolved == 0
                               && !deadOption && noCallers.isEmpty()
                           ? "consistent"
                           : "SUSPECT - a sink resolved to nothing, a site would not decompile, an "
                             + "accessor call's parameter name could not be read, or a declared "
                             + "accessor never matched; those rows are unmeasured, not clean");
            out.println("  \"call_sites\": [");
            out.println(String.join(",\n", rows));
            out.println("  ]");
            out.println("}");
        }
        println(String.format("BoaArgTrace: %d sites in scope, %d traced, %d untraced, wrote %s",
                              siteCount, rows.size(), failed, outPath));
    }

    // ------------------------------------------------------------- provenance

    /**
     * Walk one argument backwards through the SSA form.
     *
     * The recursion stops at the first thing that is worth naming: a string
     * literal, a request parameter, a stack slot, a constant, or a call whose
     * result is being passed straight through. Everything is reported with a
     * `kind` so that a reader can tell "this is a literal" from "this is a value
     * I could not follow", which are opposite conclusions about safety.
     */
    private String describe(Varnode vn, int frameSize, int depth, Set<String> mentions) {
        if (vn == null) {
            return "\"kind\":\"null\"";
        }
        if (depth <= 0) {
            return "\"kind\":\"depth-exhausted\"";
        }
        // One resolver, used here and by firstLiteralArg. The first version of
        // this script had two, and they drifted: `describe` could see the string
        // "targetAPSsid" while `firstLiteralArg` could not, so every
        // request parameter that reached a sink through sprintf was reported as
        // an anonymous `call-result`. The census said 1 tainted call site out of
        // 304 and W03 had already found three by hand — which is the only reason
        // it was caught. Duplicated resolution logic is the bug; one function is
        // the fix.
        String lit = literalOf(vn, 4);
        if (lit != null) {
            return String.format("\"kind\":\"literal\",\"addr\":\"%08x\",\"text\":\"%s\"",
                                 constAddrOf(vn, 4), esc(lit));
        }
        if (vn.isConstant()) {
            return String.format("\"kind\":\"const\",\"value\":\"0x%x\"", vn.getOffset());
        }

        // A named stack slot is the shape an overflow claim needs a number for.
        if (vn.getHigh() != null && vn.getHigh().getSymbol() != null
                && vn.getHigh().getSymbol().getStorage() != null
                && vn.getHigh().getSymbol().getStorage().isStackStorage()) {
            int off = vn.getHigh().getSymbol().getStorage().getStackOffset();
            return String.format(
                "\"kind\":\"stack\",\"name\":\"%s\",\"offset\":%d,\"frame_size\":%d,"
                + "\"bytes_to_frame_top\":%d",
                esc(vn.getHigh().getSymbol().getName()), off, frameSize,
                off < 0 ? -off : 0);
        }

        PcodeOp def = vn.getDef();
        if (def == null) {
            return String.format("\"kind\":\"unresolved\",\"varnode\":\"%s\"", esc(vn.toString()));
        }
        switch (def.getOpcode()) {
            case PcodeOp.CALL:
            case PcodeOp.CALLIND: {
                String callee = calleeName(def);
                // The accessor that separates request data from program data.
                String p = firstLiteralArg(def);
                if (isAccessor(callee)) {
                    if (p != null) {
                        mentions.add(p);
                        return String.format(
                            "\"kind\":\"request-parameter\",\"via\":\"%s\",\"name\":\"%s\"",
                            esc(callee), esc(p));
                    }
                    // An accessor whose parameter name could not be read is the
                    // exact failure that made the first run of this script
                    // report 1 tainted call site out of 304. Counting it makes
                    // the resolver's blind spots visible in the artefact instead
                    // of turning them into a reassuring number — and naming the
                    // site makes the count something a reader can go and check.
                    accessorUnresolved++;
                    accessorUnresolvedSites.add(String.format(
                        "{\"site\":\"%s\",\"function\":\"%s\",\"accessor\":\"%s\"}",
                        esc(currentSite), esc(currentFunction), esc(callee)));
                }
                List<String> inner = new ArrayList<>();
                for (int i = 1; i < def.getNumInputs() && i <= 4; i++) {
                    inner.add("{" + describe(def.getInput(i), frameSize, depth - 1, mentions) + "}");
                }
                return String.format(
                    "\"kind\":\"call-result\",\"callee\":\"%s\",\"callee_args\":[%s]",
                    esc(callee), String.join(",", inner));
            }
            case PcodeOp.COPY:
            case PcodeOp.CAST:
            case PcodeOp.INDIRECT:
            case PcodeOp.INT_ZEXT:
            case PcodeOp.INT_SEXT:
            case PcodeOp.SUBPIECE:
                return describe(def.getInput(0), frameSize, depth - 1, mentions);
            case PcodeOp.PTRSUB:
            case PcodeOp.PTRADD:
            case PcodeOp.INT_ADD: {
                // Base + constant. If the base is the stack pointer this is a
                // stack buffer the decompiler did not give a symbol to; if it is
                // a constant it is usually a global.
                Varnode b = def.getInput(0);
                Varnode o = def.getInput(1);
                if (b != null && o != null && o.isConstant() && b.isConstant()) {
                    long v = b.getOffset() + o.getOffset();
                    Address a = toAddrSafe(v);
                    String s = a == null ? null : stringAt(a);
                    if (s != null) {
                        return String.format(
                            "\"kind\":\"literal\",\"addr\":\"%08x\",\"text\":\"%s\"", v, esc(s));
                    }
                    return String.format("\"kind\":\"global\",\"addr\":\"0x%x\"", v);
                }
                if (b != null && b.isRegister() && o != null && o.isConstant()) {
                    return String.format(
                        "\"kind\":\"reg-offset\",\"base\":\"%s\",\"offset\":%d,\"frame_size\":%d",
                        esc(regName(b)), (int) o.getOffset(), frameSize);
                }
                return describe(b, frameSize, depth - 1, mentions);
            }
            case PcodeOp.MULTIEQUAL: {
                // A phi node: the value depends on which branch ran. Both sides
                // matter, so both are reported rather than one being picked.
                List<String> sides = new ArrayList<>();
                for (int i = 0; i < def.getNumInputs() && i < 4; i++) {
                    sides.add("{" + describe(def.getInput(i), frameSize, depth - 1, mentions) + "}");
                }
                return String.format("\"kind\":\"phi\",\"from\":[%s]", String.join(",", sides));
            }
            case PcodeOp.LOAD:
                return String.format("\"kind\":\"load\",\"from\":{%s}",
                                     describe(def.getInput(1), frameSize, depth - 1, mentions));
            default:
                return String.format("\"kind\":\"op\",\"opcode\":\"%s\"",
                                     esc(def.getMnemonic()));
        }
    }

    /**
     * The Realtek accessors that hand a request parameter to a handler.
     *
     * Kept as a list rather than "any call with a string argument" because the
     * distinction being drawn — attacker data versus program data — is the whole
     * point, and widening it would make every `strcmp` look like an input source.
     * V3.4.0 is stripped, so an unnamed function is accepted when it is the sole
     * two-string-argument accessor; that case is marked `via` in the output so
     * the weaker identification stays visible.
     */
    private boolean isAccessor(String callee) {
        String n = callee.toLowerCase();
        // Lowercased on both sides. It was not, and `accessor:FUN_0040e9e0`
        // therefore matched nothing: V3.4.0 came back with 0 tainted call
        // sites against V2.1.2's 86, for one codebase five years apart. The
        // self_check said "consistent" the whole time, because a comparison
        // that never fires also never fails. What caught it was reading the
        // two builds across instead of down. Hence the
        // accessor_declared_but_never_matched flag in the self_check: an
        // option that had no effect is now an error, not a silence.
        boolean overridden = !accessorOverride.isEmpty()
                             && n.equals(accessorOverride.toLowerCase());
        if (overridden) {
            accessorOverrideMatched = true;
        }
        boolean hit = overridden
            || n.contains("get_cstream_var") || n.contains("getvar")
            || n.contains("boa_getvar") || n.contains("req_get");
        if (hit) {
            accessorMatches++;
        }
        return hit;
    }

    /** Set with `accessor:FUN_00412345` when the build is stripped. */
    private String accessorOverride = "";
    private boolean accessorOverrideMatched = false;

    /**
     * How many calls were recognised as the request-parameter accessor, by any
     * route. Zero is the condition that matters and it had no check.
     *
     * `accessor_declared_but_never_matched` only fires when an override *was*
     * passed. Run a stripped build with no override at all and the name-based
     * matcher recognises nothing, every request-parameter result is empty, and
     * the self_check reports "consistent" — because the failing option was
     * absent rather than wrong. W04-2 walked into exactly that: re-running all
     * three builds under one spec to make their scope counts comparable dropped
     * V3.4.0's accessor override, and its tainted-site count went 49 -> 0 with
     * a clean verdict. Same 86 -> 0 shape as W04, arriving this time through
     * *how the tool was called* rather than through what it does.
     *
     * The tool cannot know which accessor a stripped build uses. It can know
     * that it never found one, and refuse to call that result clean.
     */
    private int accessorMatches = 0;

    private String firstLiteralArg(PcodeOp call) {
        for (int i = 1; i < call.getNumInputs(); i++) {
            String s = literalOf(call.getInput(i), 4);
            if (s != null && !s.isEmpty()) {
                return s;
            }
        }
        return null;
    }

    /**
     * The address a varnode ultimately names, if it names one.
     *
     * A pointer to a string literal reaches a call in several shapes depending
     * on how the compiler materialised it: a bare constant, `PTRSUB(base,off)`,
     * `PTRADD`, an `INT_ADD` of two constants, or any of those behind a
     * COPY/CAST/INDIRECT. Following all of them in one place is what keeps the
     * two callers agreeing.
     */
    private long constAddrOf(Varnode vn, int depth) {
        if (vn == null || depth <= 0) {
            return -1;
        }
        if (vn.isConstant()) {
            return vn.getOffset();
        }
        PcodeOp def = vn.getDef();
        if (def == null) {
            return -1;
        }
        switch (def.getOpcode()) {
            case PcodeOp.PTRSUB:
            case PcodeOp.PTRADD:
            case PcodeOp.INT_ADD: {
                Varnode b = def.getInput(0);
                Varnode o = def.getInput(1);
                if (b != null && o != null && b.isConstant() && o.isConstant()) {
                    return b.getOffset() + o.getOffset();
                }
                return -1;
            }
            case PcodeOp.COPY:
            case PcodeOp.CAST:
            case PcodeOp.INDIRECT:
                return constAddrOf(def.getInput(0), depth - 1);
            default:
                return -1;
        }
    }

    private String literalOf(Varnode vn, int depth) {
        long v = constAddrOf(vn, depth);
        if (v < 0) {
            return null;
        }
        Address a = toAddrSafe(v);
        return a == null ? null : stringAt(a);
    }

    private String calleeName(PcodeOp call) {
        Varnode t = call.getInput(0);
        if (t == null || !t.isAddress()) {
            return "indirect";
        }
        Function f = getFunctionAt(t.getAddress());
        if (f == null) {
            Symbol s = getSymbolAt(t.getAddress());
            return s != null ? s.getName() : t.getAddress().toString();
        }
        if (f.getName().startsWith("FUN_") && isStub(f)) {
            String only = stubSymbol(f);
            if (only != null) {
                return only + "@plt";
            }
        }
        return f.getName();
    }

    // ------------------------------------------------------------- resolution

    /**
     * Delegated to {@link BoaPlt} on purpose. The first version of this method
     * re-implemented the resolution and left out the constructed-PLT route, so
     * `strcpy` produced 151 tainted call sites in V2.1.2 and 0 in V3.4.0 while
     * `system` and `sprintf` were fine. One resolver, one place to fix.
     */
    private Set<Address> resolveTargets(String name) {
        return BoaPlt.callTargets(this, name);
    }

    private boolean inScope(Function f, List<String> scopes) {
        if (scopes.isEmpty()) {
            return true;
        }
        for (String s : scopes) {
            if (f.getName().startsWith(s)) {
                return true;
            }
        }
        return false;
    }

    private PcodeOpAST callOpAt(HighFunction hf, Address at) {
        Iterator<PcodeOpAST> it = hf.getPcodeOps(at);
        while (it.hasNext()) {
            PcodeOpAST op = it.next();
            if (op.getOpcode() == PcodeOp.CALL || op.getOpcode() == PcodeOp.CALLIND) {
                return op;
            }
        }
        return null;
    }

    private boolean isStub(Function f) {
        return BoaPlt.isStub(this, f);
    }

    private String stubSymbol(Function f) {
        String only = null;
        InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            for (Reference r : ins.getReferencesFrom()) {
                Symbol s = getSymbolAt(r.getToAddress());
                if (s == null) {
                    continue;
                }
                String n = s.getName();
                if (n.startsWith("FUN_") || n.startsWith("DAT_")
                        || n.startsWith("PTR_") || n.startsWith("LAB_")) {
                    continue;
                }
                if (only != null && !only.equals(n)) {
                    return null;
                }
                only = n;
            }
        }
        return only;
    }

    private int instructionCount(Function f) {
        int n = 0;
        InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
        while (it.hasNext() && n <= STUB_MAX_INSTRUCTIONS + 1) {
            it.next();
            n++;
        }
        return n;
    }

    private String regName(Varnode v) {
        var r = currentProgram.getRegister(v.getAddress());
        return r != null ? r.getName() : v.toString();
    }

    private Address toAddrSafe(long v) {
        try {
            if (v < 0x400000L || v > 0x600000L) {
                return null;
            }
            return toAddr(v);
        } catch (Exception e) {
            return null;
        }
    }

    private String stringAt(Address a) {
        try {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 200; i++) {
                int c = getByte(a.add(i)) & 0xFF;
                if (c == 0) {
                    break;
                }
                if (c != '\t' && c != '\n' && c != '\r' && (c < 0x20 || c > 0x7E)) {
                    return null;
                }
                sb.append((char) c);
            }
            return sb.length() >= 2 ? sb.toString() : null;
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
