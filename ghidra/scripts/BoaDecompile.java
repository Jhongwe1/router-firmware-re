/* BoaDecompile.java — export decompiled C for named functions, for reading.
 *
 * Why this exists
 * ---------------
 * The reading is the work. This only moves the decompiler's output somewhere it
 * can be read, diffed between the 2015 and 2020 builds, and quoted in notes
 * with a stable address next to it — instead of living in one person's GUI.
 *
 * Where the output goes, and why not into the repository
 * ------------------------------------------------------
 * Into ghidra/decomp/, which is gitignored. Decompiled C of a vendor binary is
 * a derivative of that binary; committing the whole corpus is redistribution of
 * the firmware by another route, and this project's stated position is that the
 * firmware is not redistributed. Short excerpts quoted inside an analysis, with
 * commentary, are a different thing and those do get committed.
 *
 * Selectors (2nd script argument onward)
 *   prefix:form_      every function whose name starts with form_
 *   name:handleForm   one function by exact name
 *   @00440eec         one function by entry address
 *   callers:system    every function containing a reference to `system`
 *   string:AUTHG_IP   every function referencing a string containing this text.
 *                     The only handle on a function in the sstrip'd V3.4.0
 *                     build, where nothing is named and the 2015 build's
 *                     surviving symbols have no counterpart — a literal is
 *                     often the only thing the two builds still share.
 *
 * Usage:
 *   -postScript BoaDecompile.java <index.json> <sha256|-> <selector> [<selector>...]
 */

import java.io.File;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class BoaDecompile extends GhidraScript {

    private static final int TIMEOUT_SECONDS = 90;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            println("BoaDecompile: need <index.json> <sha256|-> <selector>...");
            return;
        }
        String indexPath = args[0];
        String sha = "-".equals(args[1]) ? "" : args[1];

        File outDir = new File(new File(indexPath).getAbsoluteFile().getParentFile(),
                               stem(indexPath));
        if (!outDir.exists() && !outDir.mkdirs()) {
            throw new Exception("could not create " + outDir);
        }

        Map<Function, String> selected = new LinkedHashMap<>();
        for (int i = 2; i < args.length; i++) {
            for (Function f : resolve(args[i])) {
                selected.putIfAbsent(f, args[i]);
            }
        }

        DecompInterface di = new DecompInterface();
        di.setOptions(new DecompileOptions());
        if (!di.openProgram(currentProgram)) {
            throw new Exception("decompiler would not open the program: " + di.getLastMessage());
        }

        List<String> rows = new ArrayList<>();
        int ok = 0, failed = 0;
        try {
            for (var kv : selected.entrySet()) {
                monitor.checkCancelled();
                Function fn = kv.getKey();
                String file = safe(fn.getName()) + "@" + fn.getEntryPoint() + ".c";
                String status;
                DecompileResults res = di.decompileFunction(fn, TIMEOUT_SECONDS, monitor);
                if (res != null && res.decompileCompleted()
                        && res.getDecompiledFunction() != null) {
                    try (PrintWriter w = new PrintWriter(new File(outDir, file), "UTF-8")) {
                        w.println("/* " + currentProgram.getName()
                                  + "  " + fn.getName()
                                  + "  entry=" + fn.getEntryPoint()
                                  + "  selector=" + kv.getValue() + " */");
                        w.print(res.getDecompiledFunction().getC());
                    }
                    status = "ok";
                    ok++;
                } else {
                    // Recorded rather than skipped: a function the decompiler
                    // refuses is itself worth knowing about, and silence here
                    // would look identical to "no such function".
                    status = res == null ? "null-result" : esc(res.getErrorMessage());
                    failed++;
                }
                rows.add(String.format(
                    "    {\"function\":\"%s\",\"entry\":\"%s\",\"selector\":\"%s\","
                    + "\"file\":\"%s\",\"status\":\"%s\"}",
                    esc(fn.getName()), fn.getEntryPoint(), esc(kv.getValue()),
                    esc(file), esc(status)));
            }
        } finally {
            di.dispose();
        }

        try (PrintWriter out = new PrintWriter(indexPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaDecompile\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sha));
            out.printf("  \"language\": \"%s\",%n", esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"output_dir\": \"%s\",%n", esc(outDir.getAbsolutePath()));
            out.printf("  \"decompiled\": %d,%n", ok);
            out.printf("  \"failed\": %d,%n", failed);
            out.println("  \"functions\": [");
            out.println(String.join(",\n", rows));
            out.println("  ]");
            out.println("}");
        }
        println(String.format("BoaDecompile: %d ok, %d failed, into %s", ok, failed, outDir));
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
            Address a = toAddr(selector.substring(1));
            Function f = getFunctionContaining(a);
            if (f != null) {
                out.add(f);
            }
        } else if (selector.startsWith("string:")) {
            String needle = selector.substring(7);
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
                // A selector that matches nothing returns nothing; the index
                // JSON then shows zero functions for it, which is the honest
                // result and is visible rather than silent.
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

    private String stem(String path) {
        String base = new File(path).getName();
        int dot = base.lastIndexOf('.');
        return dot > 0 ? base.substring(0, dot) : base;
    }

    private String safe(String s) {
        return s.replaceAll("[^A-Za-z0-9_.-]", "_");
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
