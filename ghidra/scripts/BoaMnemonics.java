/* BoaMnemonics.java — mnemonic histogram over executable memory, and a census
 * of everything the disassembler did *not* turn into an instruction.
 *
 * The question that looks small
 * ----------------------------
 * W02 open #9 asks for a count of `lwl`/`lwr`/`swl`/`swr` in these binaries.
 * Lexra removed those four (they are MIPS-patented) from its cores, and the
 * RTL8196C's RLX4181 is usually documented without them. This unit is an
 * RTL8196E, generally recorded as RLX5281, and the public sources disagree with
 * each other about whether the 5281 has them. So: measure, do not vote.
 *
 * The question that is not small
 * ------------------------------
 * Lexra did not only *remove* instructions. It *added* a set of its own — MAC
 * (`madh`/`madl`/`mazh`/`msbh`), `lt`/`st`/`ltp`/`lwp`/`lhp`/`lbp`, and the
 * RADIAX DSP group — and it put them in opcode space that standard MIPS leaves
 * to coprocessors 2 and 3.
 *
 * That space is exactly what Ghidra's stock MIPS module *will* decode, into
 * coprocessor instructions that do not belong on a SoC with no coprocessor 2.
 * So the failure mode is not a visible error:
 *
 *     qemu on a Lexra extension -> SIGILL              (loud)
 *     Ghidra on a Lexra extension -> a plausible cop2 instruction   (silent)
 *
 * Every static result in this repository from W03 onward rests on Ghidra having
 * decoded these binaries correctly, and that assumption has never been stated,
 * let alone tested. This script tests it, and it emits three numbers rather
 * than one:
 *
 *   1. lwl/lwr/swl/swr counts                       -> the original question
 *   2. coprocessor-2/3 instructions                 -> candidate mis-decodes
 *   3. bytes inside executable blocks that are neither instruction nor defined
 *      data                                         -> what the disassembler
 *                                                     declined to touch at all
 *
 * Reading the result — and the asymmetry is the point
 * ---------------------------------------------------
 *   lwl/lwr PRESENT in the binary this unit runs
 *       -> the CPU executes them. This binary serves the web UI on this device,
 *          and an instruction that traps does not live quietly on a hot path.
 *          That is proof, and it is only available because W02 got the resident
 *          build off the flash.
 *   lwl/lwr ABSENT
 *       -> *compatible with* the Lexra subset, and nothing more. A compiler
 *          flag (-mno-unaligned and friends) produces an identical result on a
 *          core that supports them perfectly well.
 *
 * Present is proof. Absent is only compatibility. A census that reports one
 * number and lets the reader supply the direction is worse than no census.
 *
 * Usage:  -postScript BoaMnemonics.java <out.json> [<source-sha256>]
 */

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;

public class BoaMnemonics extends GhidraScript {

    /** The four Lexra dropped. Lower case; Ghidra emits lower-case MIPS mnemonics. */
    private static final String[] UNALIGNED = { "lwl", "lwr", "swl", "swr" };

    /**
     * Standard-MIPS coprocessor 2/3 encodings. On a core with no such
     * coprocessor these should not appear in compiler output at all, so any
     * hit is a candidate for a Lexra extension decoded as the wrong thing.
     * Kept as a prefix list rather than exact names because Ghidra decorates
     * some of these (`cop2`, `c2`, `mfc2`, `cfc2`, `lwc2`, ...).
     */
    private static final String[] COP23 = {
        "cop2", "cop3", "c2", "c3", "mfc2", "mtc2", "cfc2", "ctc2",
        "lwc2", "swc2", "ldc2", "sdc2", "lwc3", "swc3", "bc2", "bc3"
    };

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "mnemonics.json";
        String sha = args.length > 1 ? args[1] : "";

        Map<String, Integer> hist = new TreeMap<>();
        List<String> copSites = new ArrayList<>();
        Map<String, List<String>> unalignedSites = new LinkedHashMap<>();
        for (String m : UNALIGNED) {
            unalignedSites.put(m, new ArrayList<>());
        }

        // Only executable, initialised blocks. Counting .data would inflate the
        // "not disassembled" figure with things that were never meant to be code.
        AddressSet exec = new AddressSet();
        List<String> blocks = new ArrayList<>();
        long execBytes = 0;
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            if (b.isExecute() && b.isInitialized()) {
                exec.addRange(b.getStart(), b.getEnd());
                execBytes += b.getSize();
                blocks.add(String.format(
                    "{\"name\":\"%s\",\"start\":\"%s\",\"end\":\"%s\",\"size\":%d}",
                    esc(b.getName()), b.getStart(), b.getEnd(), b.getSize()));
            }
        }

        long instructionBytes = 0;
        long instructionCount = 0;
        InstructionIterator it = currentProgram.getListing().getInstructions(exec, true);
        while (it.hasNext()) {
            monitor.checkCancelled();
            Instruction ins = it.next();
            String m = ins.getMnemonicString().toLowerCase();
            hist.merge(m, 1, Integer::sum);
            instructionBytes += ins.getLength();
            instructionCount++;

            if (unalignedSites.containsKey(m) && unalignedSites.get(m).size() < 50) {
                unalignedSites.get(m).add(String.format(
                    "{\"at\":\"%s\",\"in\":\"%s\"}", ins.getAddress(), esc(fnName(ins.getAddress()))));
            }
            for (String c : COP23) {
                if (m.equals(c) || m.startsWith(c + ".")) {
                    if (copSites.size() < 200) {
                        copSites.add(String.format(
                            "{\"at\":\"%s\",\"mnemonic\":\"%s\",\"in\":\"%s\",\"bytes\":\"%s\"}",
                            ins.getAddress(), esc(m), esc(fnName(ins.getAddress())),
                            bytesAt(ins)));
                    }
                    break;
                }
            }
        }

        // Bytes inside executable blocks covered by neither an instruction nor
        // defined data. Not automatically a problem — alignment padding and
        // jump tables land here — but it is the quantity that has to be small
        // before "Ghidra decoded this binary" is a statement rather than a hope.
        long definedDataBytes = 0;
        for (CodeUnit cu : currentProgram.getListing().getCodeUnits(exec, true)) {
            monitor.checkCancelled();
            if (!(cu instanceof Instruction) && cu.getLength() > 0
                    && currentProgram.getListing().getDefinedDataAt(cu.getMinAddress()) != null) {
                definedDataBytes += cu.getLength();
            }
        }
        long undecoded = execBytes - instructionBytes - definedDataBytes;

        int unalignedTotal = 0;
        for (String m : UNALIGNED) {
            unalignedTotal += hist.getOrDefault(m, 0);
        }

        try (PrintWriter out = new PrintWriter(outPath, "UTF-8")) {
            out.println("{");
            out.println("  \"producer\": \"ghidra:BoaMnemonics\",");
            out.printf("  \"program\": \"%s\",%n", esc(currentProgram.getName()));
            out.printf("  \"source_sha256\": \"%s\",%n", esc(sha));
            out.printf("  \"language\": \"%s\",%n",
                       esc(currentProgram.getLanguageID().getIdAsString()));
            out.printf("  \"image_base\": \"%s\",%n", currentProgram.getImageBase());
            // Required by tools/check-reports.py: a report whose function count is
            // zero describes a program the analyser never processed, and it would
            // otherwise look identical to a real one.
            out.printf("  \"function_count\": %d,%n",
                       currentProgram.getFunctionManager().getFunctionCount());
            out.printf("  \"executable_blocks\": [%s],%n", String.join(",", blocks));
            out.printf("  \"executable_bytes\": %d,%n", execBytes);
            out.printf("  \"instruction_count\": %d,%n", instructionCount);
            out.printf("  \"instruction_bytes\": %d,%n", instructionBytes);
            out.printf("  \"defined_data_bytes\": %d,%n", definedDataBytes);
            out.printf("  \"not_decoded_bytes\": %d,%n", undecoded);
            out.printf("  \"not_decoded_fraction\": %.6f,%n",
                       execBytes == 0 ? 0.0 : (double) undecoded / (double) execBytes);
            out.printf("  \"distinct_mnemonics\": %d,%n", hist.size());

            out.printf("  \"lexra_unaligned\": {\"total\": %d", unalignedTotal);
            for (String m : UNALIGNED) {
                out.printf(",\"%s\": %d", m, hist.getOrDefault(m, 0));
            }
            out.println("},");
            out.println("  \"lexra_unaligned_sites\": {");
            List<String> us = new ArrayList<>();
            for (String m : UNALIGNED) {
                us.add(String.format("    \"%s\": [%s]", m, String.join(",", unalignedSites.get(m))));
            }
            out.println(String.join(",\n", us));
            out.println("  },");

            out.printf("  \"coprocessor_2_3_count\": %d,%n", copSites.size());
            out.printf("  \"coprocessor_2_3_sites\": [%s],%n", String.join(",", copSites));

            // The interpretation travels with the number, because the number on
            // its own points the wrong way half the time.
            out.printf("  \"reading\": \"%s\",%n",
                       unalignedTotal > 0
                           ? "lwl/lwr/swl/swr PRESENT - this binary requires them, so the core "
                             + "that runs it implements them. Proof, not compatibility."
                           : "lwl/lwr/swl/swr ABSENT - COMPATIBLE with the Lexra subset and "
                             + "nothing more. A compiler flag produces the same result on a core "
                             + "that supports them. Absence is not evidence the CPU lacks them.");

            // A histogram that cannot fail proves nothing. Two ways this one can:
            // an executable region the disassembler mostly declined, and any
            // coprocessor-2/3 instruction at all on a SoC that has no such unit.
            boolean copSuspect = !copSites.isEmpty();
            boolean coverageSuspect = execBytes > 0
                    && (double) undecoded / (double) execBytes > 0.02;
            out.printf("  \"self_check\": {\"coprocessor_2_3_present\": %b,"
                       + "\"not_decoded_over_2_percent\": %b,\"verdict\": \"%s\"},%n",
                       copSuspect, coverageSuspect,
                       (copSuspect || coverageSuspect)
                           ? "SUSPECT - coprocessor 2/3 encodings and undecoded runs are where a "
                             + "Lexra extension would hide as a plausible standard instruction; "
                             + "these addresses need reading before any static result over them "
                             + "is trusted"
                           : "consistent - no coprocessor 2/3 encodings, and the disassembler "
                             + "covered executable memory");

            out.println("  \"mnemonics\": {");
            List<String> rows = new ArrayList<>();
            for (var kv : hist.entrySet()) {
                rows.add(String.format("    \"%s\": %d", esc(kv.getKey()), kv.getValue()));
            }
            out.println(String.join(",\n", rows));
            out.println("  }");
            out.println("}");
        }

        println(String.format(
            "BoaMnemonics: %d instructions, %d distinct mnemonics, lwl/lwr/swl/swr=%d, "
            + "cop2/3=%d, not-decoded=%d bytes (%.3f%%), wrote %s",
            instructionCount, hist.size(), unalignedTotal, copSites.size(), undecoded,
            execBytes == 0 ? 0.0 : 100.0 * undecoded / execBytes, outPath));
    }

    private String fnName(Address a) {
        var f = getFunctionContaining(a);
        return f == null ? "" : f.getName();
    }

    private String bytesAt(Instruction ins) {
        try {
            StringBuilder sb = new StringBuilder();
            for (byte b : ins.getBytes()) {
                sb.append(String.format("%02x", b & 0xFF));
            }
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
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
