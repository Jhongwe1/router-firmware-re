/* BoaPlt.java — one place that knows how a call reaches libc in these binaries.
 *
 * Why this is its own file
 * ------------------------
 * V3.4.0 is `sstrip`'d: no section headers, so Ghidra cannot find `.plt` and
 * only turns *some* PLT entries into functions. `system` and `sprintf` get one;
 * `strcpy` and `strcat` do not. A script that resolves a sink by asking "what
 * references this symbol" therefore sees every `strcpy` call site in the 2015
 * build and **none** in the 2020 build, and reports that as a fact about the
 * firmware.
 *
 * That has now happened twice in this project:
 *
 *   W03  BoaSinks       589 strcpy call sites in V2.1.2, 1 in V3.4.0
 *   W04  BoaArgTrace    151 tainted strcpy sites in V2.1.2, 0 in V3.4.0
 *
 * The second time, BoaSinks already contained the fix. It was not reused; it was
 * re-implemented, and the re-implementation was missing the part that mattered.
 * Duplicated resolution logic is the defect, so the logic lives here and both
 * scripts call it. The comparison that caught it both times was reading the two
 * builds across rather than down.
 *
 * The construction
 * ----------------
 * A PLT entry is not searched for heuristically. binutils emits a fixed
 * four-instruction sequence per MIPS PLT slot, every field determined by the
 * `.got.plt` slot address S:
 *
 *   lui   $15, %hi(S)        3C 0F hi
 *   lw    $25, %lo(S)($15)   8D F9 lo
 *   addiu $24, $15, %lo(S)   25 F8 lo
 *   jr    $25                03 20 00 08
 *
 * so the stub is computed and then required to exist at exactly one address. A
 * pattern that matches twice, or not at all, returns nothing rather than a
 * guess.
 */

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public final class BoaPlt {

    /** Longest plausible MIPS PLT / lazy-binding stub, in instructions. */
    public static final int STUB_MAX_INSTRUCTIONS = 8;

    private BoaPlt() {
    }

    /**
     * Every address a call to {@code name} can land on: the symbol itself, any
     * function already carrying the name, and the PLT stubs in front of them.
     */
    public static Set<Address> callTargets(GhidraScript s, String name) {
        Set<Address> seeds = seeds(s, name);
        Set<Address> out = new LinkedHashSet<>(seeds);
        out.addAll(stubs(s, seeds, name));
        return out;
    }

    /** The seeds alone — useful for telling "imported" from "has callers". */
    public static Set<Address> seeds(GhidraScript s, String name) {
        Set<Address> out = new LinkedHashSet<>();
        SymbolIterator si = s.getCurrentProgram().getSymbolTable().getSymbols(name);
        while (si.hasNext()) {
            Symbol sym = si.next();
            if (sym.getAddress() != null) {
                out.add(sym.getAddress());
            }
        }
        FunctionIterator fit = s.getCurrentProgram().getFunctionManager().getFunctions(true);
        while (fit.hasNext()) {
            Function f = fit.next();
            String n = f.getName();
            if (n.equals(name) || n.equals("." + name) || n.equals("__" + name)
                    || n.equals(name + "_plt")) {
                out.add(f.getEntryPoint());
            }
        }
        return out;
    }

    /**
     * Stub-shaped functions standing in front of the seeds, by two routes.
     *
     * The first route finds stubs Ghidra already turned into functions. The
     * second constructs the entry for each `.got.plt` slot, which is the only
     * route that works for the sinks Ghidra never disassembled.
     */
    public static Set<Address> stubs(GhidraScript s, Set<Address> seeds, String name) {
        Set<Address> out = new LinkedHashSet<>();
        for (Address a : seeds) {
            for (Reference r : s.getReferencesTo(a)) {
                Function f = s.getFunctionContaining(r.getFromAddress());
                if (f == null || seeds.contains(f.getEntryPoint())) {
                    continue;
                }
                if (f.isThunk() || instructionCount(s, f) <= STUB_MAX_INSTRUCTIONS) {
                    out.add(f.getEntryPoint());
                }
            }
        }
        for (Address slot : gotSlots(s, seeds)) {
            Address stub = stubForSlot(s, slot);
            if (stub == null) {
                continue;
            }
            out.add(stub);
            if (s.getFunctionAt(stub) == null) {
                try {
                    s.disassemble(stub);
                    s.createFunction(stub, name + "_plt");
                } catch (Exception ignored) {
                    // Counting callers does not depend on it becoming a
                    // function; the label is a convenience for the GUI.
                }
            }
        }
        return out;
    }

    /**
     * The `.got.plt` slots holding a symbol's address. A data reference to an
     * external symbol from outside any function is a relocation target, not
     * code — which is also why such references must never be counted as calls.
     */
    public static Set<Address> gotSlots(GhidraScript s, Set<Address> seeds) {
        Set<Address> out = new LinkedHashSet<>();
        for (Address a : seeds) {
            for (Reference r : s.getReferencesTo(a)) {
                if (r.getReferenceType().isData()
                        && s.getFunctionContaining(r.getFromAddress()) == null) {
                    out.add(r.getFromAddress());
                }
            }
        }
        return out;
    }

    /** The one address the PLT entry for {@code slot} must be at, or null. */
    public static Address stubForSlot(GhidraScript s, Address slot) {
        long v = slot.getOffset();
        int hi = (int) (((v + 0x8000) >> 16) & 0xFFFF);
        int lo = (int) (v & 0xFFFF);
        byte[] sig = new byte[] {
            0x3C, 0x0F, (byte) (hi >> 8), (byte) hi,
            (byte) 0x8D, (byte) 0xF9, (byte) (lo >> 8), (byte) lo,
            0x25, (byte) 0xF8, (byte) (lo >> 8), (byte) lo,
            0x03, 0x20, 0x00, 0x08,
        };
        Address found = null;
        Address at = s.getCurrentProgram().getMinAddress();
        while (at != null) {
            Address hit = s.find(at, sig);
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
     * Sinks the binary imports for which no call site was found anywhere in the
     * program. Non-empty means the resolver failed, not that the code is clean.
     */
    public static List<String> importedWithNoCallers(GhidraScript s, List<String> names) {
        List<String> suspect = new ArrayList<>();
        for (String n : names) {
            Set<Address> seeds = seeds(s, n);
            if (seeds.isEmpty()) {
                continue;               // not imported: silence is correct here
            }
            Set<Address> targets = callTargets(s, n);
            boolean any = false;
            for (Address t : targets) {
                for (Reference r : s.getReferencesTo(t)) {
                    if (!r.getReferenceType().isCall() && !r.getReferenceType().isJump()) {
                        continue;
                    }
                    Function c = s.getFunctionContaining(r.getFromAddress());
                    if (c != null && !targets.contains(c.getEntryPoint())) {
                        any = true;
                        break;
                    }
                }
                if (any) {
                    break;
                }
            }
            if (!any) {
                suspect.add(n);
            }
        }
        return suspect;
    }

    public static boolean isStub(GhidraScript s, Function f) {
        return f.isThunk() || instructionCount(s, f) <= STUB_MAX_INSTRUCTIONS;
    }

    private static int instructionCount(GhidraScript s, Function f) {
        int n = 0;
        InstructionIterator it =
            s.getCurrentProgram().getListing().getInstructions(f.getBody(), true);
        while (it.hasNext() && n <= STUB_MAX_INSTRUCTIONS + 1) {
            it.next();
            n++;
        }
        return n;
    }
}
