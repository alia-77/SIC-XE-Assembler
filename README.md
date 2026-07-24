# SIC/XE Assembler

A two-pass assembler for the SIC/XE architecture, written in Python. Takes SIC/XE assembly source and produces the object program (H/T/M/E records), the symbol table, and intermediate pass output.

## What it supports

- **Instruction formats 1-4**, including extended format (`+`) instructions
- **Addressing modes**: immediate (`#`), indirect (`@`), indexed (`,X`), PC-relative and base-relative displacement
- **Directives**: `START`, `END`, `BASE`, `EQU`, `WORD`, `BYTE`, `RESW`, `RESB`, `LTORG`
- **Literals** (`=C'...'`, `=X'...'`), collected into a literal pool and placed either at `LTORG` or after `END` if none is given
- **Modification records** for format-4 addresses referencing external/relocatable symbols
- **Custom format-4 instructions** (`CADD`, `CSUB`, `CLOAD`, `CSTORE`) with their own encoding scheme, distinct from the standard SIC/XE opcode format, an extension on top of the base architecture

## Pipeline

**Pass 1** builds the symbol table and location counter for each line, resolving `EQU`, `BASE`, and literal placement.

**Pass 2** walks the pass-1 output and generates the object code for each instruction, using the symbol table for address resolution and choosing between PC-relative, base-relative, or extended (format-4) addressing depending on displacement range.

**Output** writes five files: `intermediate.txt`, `out_pass1.txt`, `out_pass2.txt`, `symbTable.txt`, and `HTME.txt` (the H/T/M/E object program records).

## A bug worth mentioning

One early version computed program length as `p2[-1][0] + 3 - start_addr`, i.e. from the address of the last entry in the pass-2 output. That broke as soon a source file had literals with no explicit `LTORG`: those literals get appended *after* `END`, pushing the location counter past where the actual program ends, which inflated the length recorded in the H record.

The fix: find the location of the actual `END` line explicitly and compute the length from that, instead of trusting the last emitted entry.
```python
end_loc = None
for loc, line, obj in p2:
    tokens = line.strip().split()
    if len(tokens) >= 2 and tokens[0] == 'END':
        end_loc = loc
prog_len = end_loc - start_addr
```

## Run it
```bash
python3 assembler.py --data in.txt
```
Outputs `intermediate.txt`, `out_pass1.txt`, `out_pass2.txt`, `symbTable.txt`, and `HTME.txt` in the same directory.

## Sample programs
- `in.txt` — a record read/write routine using `RDREC`/`WRREC` subroutines, base-relative and immediate addressing, and literal pool usage
- `input.txt` — a table-sum loop using indexed addressing and the custom `CADD` instruction

## Stack
Python
