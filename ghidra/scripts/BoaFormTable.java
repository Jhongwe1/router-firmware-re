/* BoaFormTable.java — recover Realtek Boa's `root_form[]` dispatch table.
 *
 * The question
 * ------------
 * W01 established that `/boafrm/<name>` is the whole request surface of this
 * device, and that the string "formSysCmd" is absent from both `boa` binaries
 * even though the CVE-2019-19824 feature is compiled in. Both facts are about
 * one array. Recovering it turns "59 strings that look like handler names" into
 * "these are the names the dispatcher will actually match, and this is the
 * function each one runs".
 *
 * The structure, and why it is not what the published source says
 * ---------------------------------------------------------------
 * The public rtl819x SDK declares the table element as
 *
 *     typedef struct { char name[80]; void (*function)(request*, int, char**); } form_name_t;
 *
 * i.e. the name stored *inline*, 84 bytes per entry. In these binaries it is
 * not: the name is a pointer, and entries are 8 bytes apart. So this script
 * does not assume either layout — it tests for the shape
 *
 *     [ptr-to-C-string][ptr-into-executable-memory]
 *
 * repeating on an 8-byte stride, and reports the runs it finds with their
 * length. If a future image really does use the 84-byte inline form, the run
 * detection here will find nothing and say so, rather than emitting garbage.
 * A recovery script that cannot fail is not evidence of anything.
 *
 * Side effect (deliberate)
 * ------------------------
 * Every recovered handler is given a real name in the program database
 * (`form_<name>`) and a plate comment recording where the name came from. The
 * W03 plan asks for "at least 5 functions renamed in Ghidra"; doing it from the
 * table means the naming is derived from evidence, applies to all of them, and
 * survives a re-import — instead of five names typed into one person's GUI.
 *
 * Usage:  -postScript BoaFormTable.java <out.json> [<source-sha256>]
 */

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.SourceType;

public class BoaFormTable extends GhidraScript {

    /** 8 = {char *name; void (*fn)();} on a 32-bit target. */
    private static final int STRIDE = 8;
    /** Shorter runs than this are coincidence: two adjacent pointers happen often. */
    private static final int MIN_RUN = 5;

    private static class Entry {
        Address entryAddr, nameAddr, handler;
        String name, previousName, finalName, action;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "form-table.json";
        String sourceSha = args.length > 1 ? args[1] : "";

        List<List<Entry>> runs = findRuns();

        // Name the handlers. Done before serialising so the JSON records both
        // what the function was called and what it is called now.
        Set<String> alreadyNamed = new LinkedHashSet<>();
        int renamed = 0;
        for (List<Entry> run : runs) {
            String prefix = rolePrefix(run);
            for (Entry e : run) {
                if (nameHandler(e, prefix, alreadyNamed)) {
                    renamed++;
                }
            }
        }

        writeJson(outPath, sourceSha, runs, renamed);

        int total = 0;
        for (List<Entry> r : runs) {
            total += r.size();
        }
        println(String.format(
                "BoaFormTable: %d table(s), %d entries, %d functions named, wrote %s",
                runs.size(), total, renamed, outPath));
    }

    // ------------------------------------------------------------------ scan

    /**
     * Walk every initialised byte on an 8-byte-aligned grid and collect maximal
     * runs of consecutive {string-pointer, code-pointer} pairs.
     *
     * Both phases of the grid (offset 0 and offset 4) are scanned, because
     * nothing guarantees the table starts on a 8-byte boundary — only that its
     * entries are 8 bytes apart.
     */
    private List<List<Entry>> findRuns() throws Exception {
        TreeMap<Address, Entry> candidates = new TreeMap<>();

        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized()) {
                continue;
            }
            Address start = block.getStart();
            long len = block.getSize();
            for (long off = 0; off + STRIDE <= len; off += 4) {
                monitor.checkCancelled();
                Address at = start.add(off);
                Entry e = tryEntry(at);
                if (e != null) {
                    candidates.put(at, e);
                }
            }
        }

        List<List<Entry>> runs = new ArrayList<>();
        List<Entry> current = new ArrayList<>();
        Address expected = null;
        for (var kv : candidates.entrySet()) {
            if (expected != null && kv.getKey().equals(expected)) {
                current.add(kv.getValue());
            } else {
                if (current.size() >= MIN_RUN) {
                    runs.add(current);
                }
                current = new ArrayList<>();
                current.add(kv.getValue());
            }
            expected = kv.getKey().add(STRIDE);
        }
        if (current.size() >= MIN_RUN) {
            runs.add(current);
        }
        return runs;
    }

    /** Does {@code at} look like one table entry? Null if not. */
    private Entry tryEntry(Address at) {
        try {
            Address nameAddr = ptrAt(at);
            Address fnAddr = ptrAt(at.add(4));
            if (nameAddr == null || fnAddr == null) {
                return null;
            }
            if (!isExecutable(fnAddr) || (fnAddr.getOffset() & 3) != 0) {
                return null;
            }
            String s = cstringAt(nameAddr);
            if (s == null) {
                return null;
            }
            Entry e = new Entry();
            e.entryAddr = at;
            e.nameAddr = nameAddr;
            e.handler = fnAddr;
            e.name = s;
            return e;
        } catch (Exception ex) {
            return null;
        }
    }

    private Address ptrAt(Address at) {
        try {
            long v = getInt(at) & 0xFFFFFFFFL;
            if (v == 0) {
                return null;
            }
            Address a = toAddr(v);
            return currentProgram.getMemory().contains(a) ? a : null;
        } catch (Exception e) {
            return null;
        }
    }

    private boolean isExecutable(Address a) {
        MemoryBlock b = currentProgram.getMemory().getBlock(a);
        return b != null && b.isExecute() && b.isInitialized();
    }

    /**
     * A NUL-terminated identifier-shaped string. Deliberately strict: allowing
     * spaces or punctuation makes half the rodata look like a handler name and
     * the run detection then finds "tables" everywhere.
     */
    private String cstringAt(Address a) {
        try {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 64; i++) {
                int c = getByte(a.add(i)) & 0xFF;
                if (c == 0) {
                    break;
                }
                boolean ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                          || (c >= '0' && c <= '9') || c == '_';
                if (!ok) {
                    return null;
                }
                sb.append((char) c);
            }
            String s = sb.toString();
            if (s.length() < 3) {
                return null;
            }
            char c0 = s.charAt(0);
            boolean alpha = (c0 >= 'a' && c0 <= 'z') || (c0 >= 'A' && c0 <= 'Z');
            return alpha ? s : null;
        } catch (Exception e) {
            return null;
        }
    }

    // ------------------------------------------------------------- annotate

    /**
     * Which of the two tables is this? Realtek's asp_page.c carries both the
     * `/boafrm/` form dispatch table and the table of names callable from
     * `<% ... %>` inside a page, and they are structurally identical — same
     * element type, adjacent in memory. Only the contents tell them apart, so
     * the prefix is decided by content rather than by table order, which would
     * be an assumption about link layout.
     */
    private String rolePrefix(List<Entry> run) {
        int formish = 0;
        for (Entry e : run) {
            String n = e.name.toLowerCase();
            if (n.startsWith("form") || n.startsWith("from")) {
                formish++;
            }
        }
        return (formish * 2 >= run.size()) ? "form_" : "aspvar_";
    }

    /** Create/name the handler and record provenance in a plate comment. */
    private boolean nameHandler(Entry e, String prefix, Set<String> alreadyNamed) {
        try {
            Function fn = getFunctionAt(e.handler);
            if (fn == null) {
                fn = getFunctionContaining(e.handler);
                if (fn != null && !fn.getEntryPoint().equals(e.handler)) {
                    // Pointer into the middle of a function: report, do not rename.
                    e.previousName = fn.getName();
                    e.finalName = fn.getName();
                    e.action = "interior-pointer-not-named";
                    return false;
                }
                fn = createFunction(e.handler, null);
            }
            if (fn == null) {
                e.previousName = "";
                e.finalName = "";
                e.action = "no-function";
                return false;
            }
            e.previousName = fn.getName();
            String want = prefix + e.name;
            String plate = "registered as \"" + e.name + "\""
                         + ("form_".equals(prefix) ? " in root_form[] -> /boafrm/" + e.name
                                                   : " in the ASP page-variable table")
                         + "\ntable entry " + e.entryAddr + ", name string " + e.nameAddr
                         + "\nnamed by ghidra/scripts/BoaFormTable.java";

            // Two cases where renaming would destroy information rather than add
            // it: a symbol that survived stripping is worth more than a name this
            // script can derive, and a function reached from two table entries
            // can only carry one name. Both get a label instead, so the extra
            // name is visible without the original being lost.
            boolean synthetic = e.previousName.startsWith("FUN_")
                             || e.previousName.startsWith("form_")
                             || e.previousName.startsWith("aspvar_");
            boolean duplicate = !alreadyNamed.add(fn.getEntryPoint().toString());

            if (!synthetic || duplicate) {
                createLabel(fn.getEntryPoint(), want, false, SourceType.USER_DEFINED);
                e.finalName = e.previousName;
                e.action = duplicate ? "label-added-duplicate-handler"
                                     : "label-added-original-symbol-kept";
                setPlateComment(fn.getEntryPoint(), plate);
                return false;
            }

            fn.setName(want, SourceType.USER_DEFINED);
            e.finalName = want;
            e.action = "renamed";
            setPlateComment(fn.getEntryPoint(), plate);
            return true;
        } catch (Exception ex) {
            e.finalName = "ERROR:" + ex.getMessage();
            e.action = "error";
            return false;
        }
    }

    /** Who reads this table? The function referencing its base is the dispatcher. */
    private String referencedBy(Address tableStart) {
        Set<String> fns = new LinkedHashSet<>();
        // The base may be reached by a reference to the table itself or to its
        // first element's name field, which are the same address on MIPS.
        for (Reference r : getReferencesTo(tableStart)) {
            Function f = getFunctionContaining(r.getFromAddress());
            fns.add(String.format("{\"from\":\"%s\",\"function\":\"%s\",\"type\":\"%s\"}",
                    r.getFromAddress(), f == null ? "" : esc(f.getName()),
                    r.getReferenceType().getName()));
        }
        return "[" + String.join(",", fns) + "]";
    }

    /**
     * String constants referenced from inside a handler. On MIPS a string
     * address is built with lui/addiu, and Ghidra's constant-reference analyser
     * turns that pair into a reference — so the handler's referenced strings are
     * recoverable without decompiling, and they are mostly the names of the
     * request parameters the handler reads. That is the cheap index of what is
     * user-controllable in each handler.
     */
    private Set<String> referencedStrings(Function fn) {
        Set<String> out = new LinkedHashSet<>();
        if (fn == null) {
            return out;
        }
        try {
            for (Instruction ins : currentProgram.getListing().getInstructions(fn.getBody(), true)) {
                for (Reference r : ins.getReferencesFrom()) {
                    Address t = r.getToAddress();
                    if (t == null || !currentProgram.getMemory().contains(t)) {
                        continue;
                    }
                    String s = printableAt(t);
                    if (s != null) {
                        out.add(s);
                    }
                    if (out.size() > 400) {
                        return out;
                    }
                }
            }
        } catch (Exception ignored) {
            // A handler whose body cannot be walked still gets an entry, just
            // without its strings. Losing one row beats losing the table.
        }
        return out;
    }

    /** Looser than cstringAt: any printable run, because parameter values and
     *  format strings matter here and they contain spaces and punctuation. */
    private String printableAt(Address a) {
        try {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 200; i++) {
                int c = getByte(a.add(i)) & 0xFF;
                if (c == 0) {
                    break;
                }
                if (c < 0x20 || c > 0x7E) {
                    return null;
                }
                sb.append((char) c);
            }
            return sb.length() >= 4 ? sb.toString() : null;
        } catch (Exception e) {
            return null;
        }
    }

    // ----------------------------------------------------------------- json

    private void writeJson(String outPath, String sourceSha,
                           List<List<Entry>> runs, int renamed) throws Exception {
        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaFormTable\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sourceSha));
            out.printf("  \"language\": \"%s\",%n", esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"entry_stride_bytes\": %d,%n", STRIDE);
            out.printf("  \"functions_named\": %d,%n", renamed);
            out.printf("  \"boafrm_prefix\": %s,%n", prefixEvidence());
            out.println("  \"tables\": [");

            List<String> tableJson = new ArrayList<>();
            for (List<Entry> run : runs) {
                List<String> rows = new ArrayList<>();
                for (Entry e : run) {
                    Function fn = getFunctionAt(e.handler);
                    Set<String> strs = referencedStrings(fn);
                    List<String> q = new ArrayList<>();
                    for (String s : strs) {
                        q.add("\"" + esc(s) + "\"");
                    }
                    rows.add(String.format(
                        "      {\"entry\":\"%s\",\"name\":\"%s\",\"name_addr\":\"%s\","
                        + "\"handler\":\"%s\",\"was\":\"%s\",\"now\":\"%s\",\"action\":\"%s\","
                        + "\"strings\":[%s]}",
                        e.entryAddr, esc(e.name), e.nameAddr, e.handler,
                        esc(nz(e.previousName)), esc(nz(e.finalName)), esc(nz(e.action)),
                        String.join(",", q)));
                }
                Address base = run.get(0).entryAddr;
                tableJson.add(String.format(
                    "    {\"address\":\"%s\",\"role\":\"%s\",\"entry_count\":%d,"
                    + "\"referenced_by\":%s,\"entries\":[%n%s%n    ]}",
                    base, "form_".equals(rolePrefix(run)) ? "root_form" : "asp_page_variables",
                    run.size(), referencedBy(base), String.join(",\n", rows)));
            }
            out.println(String.join(",\n", tableJson));
            out.println("  ]");
            out.println("}");
        }
    }

    /** Where "/boafrm/" itself lives and who reads it — that caller is handleForm. */
    private String prefixEvidence() {
        try {
            Address at = currentProgram.getMinAddress();
            List<String> hits = new ArrayList<>();
            while (at != null && hits.size() < 8) {
                Address hit = find(at, "/boafrm/".getBytes("US-ASCII"));
                if (hit == null) {
                    break;
                }
                List<String> refs = new ArrayList<>();
                for (Reference r : getReferencesTo(hit)) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    refs.add(String.format("{\"from\":\"%s\",\"function\":\"%s\"}",
                            r.getFromAddress(), f == null ? "" : esc(f.getName())));
                }
                hits.add(String.format("{\"address\":\"%s\",\"xrefs\":[%s]}",
                        hit, String.join(",", refs)));
                at = hit.add(1);
            }
            return "[" + String.join(",", hits) + "]";
        } catch (Exception e) {
            return "[]";
        }
    }

    private String nz(String s) {
        return s == null ? "" : s;
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
