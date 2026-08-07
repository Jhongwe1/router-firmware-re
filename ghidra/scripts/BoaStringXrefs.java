/* BoaStringXrefs.java — headless triage pass over a Realtek/Boa web binary.
 *
 * Purpose
 * -------
 * W01 needs a repeatable answer to "where in this binary does each interesting
 * string get used", not a screenshot of somebody clicking through the GUI. The
 * script emits JSON so the result can be diffed between firmware versions and
 * re-generated on demand.
 *
 * The keyword list is not arbitrary. Each entry is something the W01 recon
 * turned up and could not resolve from the filesystem alone — most importantly
 * the sysCmd* strings, which prove the CVE-2019-19824 feature is compiled in
 * even though the handler name "formSysCmd" is absent from the string table.
 *
 * Run via ghidra/import.ps1, or:
 *   analyzeHeadless <proj-dir> <proj> -import boa \
 *       -scriptPath ghidra/scripts -postScript BoaStringXrefs.java <out.json>
 */

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class BoaStringXrefs extends GhidraScript {

    /** Strings whose call sites answer an open question from the W01 notes. */
    private static final String[] KEYWORDS = {
        // CVE-2019-19824: the feature is present, the handler name is not.
        "sysCmd", "syscmd",
        // CVE-2019-19822/19823: config dump and its serialisation format.
        "config.dat", "COMPCS", "apmib",
        // CVE-2019-19825: CAPTCHA added between the 2015 and 2020 builds.
        "getSanvas", "topicurl",
        // The dispatch surface itself.
        "boafrm", "form", "submit-url",
        // Authentication, with no /etc/passwd anywhere in the image.
        "admin", "password", "Authorization", "realm",
        // Command construction reaching a shell.
        "/bin/sh", "cp ", "rm -rf", "echo ", "%s",
    };

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "string-xrefs.json";

        List<String> records = new ArrayList<>();
        int scanned = 0, matched = 0;

        // Deliberately using the plain Listing API rather than a string-specific
        // helper: the convenience classes for iterating defined strings have
        // been renamed across Ghidra releases (DefinedDataIterator.definedStrings
        // does not exist in 12.x), whereas getDefinedData + getValue has been
        // stable for years. A triage script that breaks on every Ghidra upgrade
        // is not reproducible.
        DataIterator it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext()) {
            monitor.checkCancelled();
            Data data = it.next();

            Object raw = data.getValue();
            if (!(raw instanceof String)) {
                continue;   // not a string datum
            }
            scanned++;

            String value = (String) raw;
            if (value.length() < 3) {
                continue;
            }
            if (!matchesKeyword(value)) {
                continue;
            }
            matched++;

            Address strAddr = data.getAddress();
            List<String> refs = new ArrayList<>();
            for (Reference ref : getReferencesTo(strAddr)) {
                Address from = ref.getFromAddress();
                Function fn = getFunctionContaining(from);
                // Reporting the containing function, not just the address, is
                // what makes the output usable: the function is the unit you
                // actually open next.
                refs.add(String.format(
                    "{\"from\":\"%s\",\"function\":\"%s\",\"function_entry\":\"%s\",\"type\":\"%s\"}",
                    from,
                    fn == null ? "" : esc(fn.getName()),
                    fn == null ? "" : fn.getEntryPoint().toString(),
                    ref.getReferenceType()));
            }

            records.add(String.format(
                "{\"address\":\"%s\",\"value\":\"%s\",\"xref_count\":%d,\"xrefs\":[%s]}",
                strAddr, esc(value), refs.size(), String.join(",", refs)));
        }

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"language\": \"%s\",%n",
                       esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"strings_scanned\": %d,%n", scanned);
            out.printf("  \"strings_matched\": %d,%n", matched);
            out.println("  \"matches\": [");
            out.println("    " + String.join(",\n    ", records));
            out.println("  ]");
            out.println("}");
        }

        println(String.format(
            "BoaStringXrefs: %d/%d strings matched, %d functions, wrote %s",
            matched, scanned,
            currentProgram.getFunctionManager().getFunctionCount(), outPath));
    }

    private boolean matchesKeyword(String value) {
        String lower = value.toLowerCase();
        for (String k : KEYWORDS) {
            if (lower.contains(k.toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    /** Minimal JSON string escaping — enough for the ASCII found in these binaries. */
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
