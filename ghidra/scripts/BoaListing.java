/* BoaListing.java — annotated disassembly for an address range.
 *
 * Why a text listing and not a screenshot
 * --------------------------------------
 * The W03 plan asks for screenshots of the Ghidra listing view. A screenshot
 * cannot be diffed between firmware versions, cannot be grepped, cannot be
 * checked by anyone who does not already trust the person who took it, and
 * cannot be regenerated after a Ghidra upgrade. A text listing can be all four.
 *
 * The specific reason this exists: the decompiler's output for
 * `process_header_end` in V2.1.2 compares the supplied credentials against two
 * stack buffers that the decompiled C never writes to, under three
 * "Heritage AFTER dead removal" warnings. Either the binary really does compare
 * against uninitialised stack, or the decompiler dropped the calls that fill
 * them. Those are very different claims about a login path, and only the
 * instructions settle it. Any conclusion drawn from decompiler output alone,
 * where the decompiler has announced that it is struggling, is a guess.
 *
 * Usage:
 *   -postScript BoaListing.java <out.txt> <sha256|-> <start-addr> <end-addr>
 */

import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;

public class BoaListing extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 4) {
            println("BoaListing: need <out.txt> <sha256|-> <start> <end>");
            return;
        }
        String outPath = args[0];
        String sha = "-".equals(args[1]) ? "" : args[1];
        Address start = toAddr(args[2]);
        Address end = toAddr(args[3]);

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("# " + currentProgram.getName()
                        + "  " + currentProgram.getLanguageID()
                        + "  base=" + currentProgram.getImageBase());
            out.println("# source_sha256=" + sha);
            out.println("# range " + start + ".." + end);
            out.println("# produced by ghidra/scripts/BoaListing.java");
            out.println();

            Instruction ins = getInstructionAt(start);
            if (ins == null) {
                ins = getInstructionAfter(start);
            }
            while (ins != null && ins.getAddress().compareTo(end) <= 0) {
                monitor.checkCancelled();
                Address a = ins.getAddress();

                Function f = getFunctionAt(a);
                if (f != null) {
                    out.println();
                    out.println("        ; ==== " + f.getName() + " ====");
                }

                // Resolved targets and string literals are what make a listing
                // readable; without them every call is `jal 0x4027a0`.
                StringBuilder note = new StringBuilder();
                for (Reference r : ins.getReferencesFrom()) {
                    Address t = r.getToAddress();
                    if (t == null) {
                        continue;
                    }
                    Function tf = getFunctionAt(t);
                    if (tf != null) {
                        note.append("  -> ").append(tf.getName());
                        continue;
                    }
                    String s = stringAt(t);
                    if (s != null) {
                        note.append("  \"").append(s).append('"');
                    } else {
                        var sym = getSymbolAt(t);
                        if (sym != null) {
                            note.append("  -> ").append(sym.getName());
                        }
                    }
                }
                out.printf("%s  %-42s%s%n", a, ins.toString(), note);
                ins = ins.getNext();
            }
        }
        println("BoaListing: wrote " + outPath);
    }

    private String stringAt(Address a) {
        try {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 120; i++) {
                int c = getByte(a.add(i)) & 0xFF;
                if (c == 0) {
                    break;
                }
                if (c < 0x20 || c > 0x7E) {
                    return null;
                }
                sb.append((char) c);
            }
            return sb.length() >= 3 ? sb.toString() : null;
        } catch (Exception e) {
            return null;
        }
    }
}
