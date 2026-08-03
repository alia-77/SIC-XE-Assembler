import sys
import os
from collections import OrderedDict

OPTAB = {
    'LDA': ('00', 3), 'STA': ('0C', 3), 'LDX': ('04', 3), 'STX': ('10', 3), 'LDB': ('68', 3),
    'ADD': ('18', 3), 'SUB': ('1C', 3), 'MUL': ('20', 3), 'DIV': ('24', 3), 'STL': ('14', 3),
    'COMP': ('28', 3), 'J': ('3C', 3), 'JEQ': ('30', 3), 'JGT': ('34', 3), 'JLT': ('38', 3),
    'JSUB': ('48', 3), 'RSUB': ('4C', 3), 'TIX': ('2C', 3), 'TD': ('E0', 3),
    'RD': ('D8', 3), 'WD': ('DC', 3), 'LDCH': ('50', 3), 'STCH': ('54', 3),
    'FIX': ('C4', 1), 'FLOAT': ('C0', 1), 'NORM': ('C8', 1), 'SIO': ('F0', 1),
    'HIO': ('F4', 1), 'TIO': ('F8', 1),
    'CLEAR': ('B4', 2), 'TIXR': ('B8', 2), 'ADDR': ('90', 2), 'SUBR': ('94', 2),
    'MULR': ('98', 2), 'DIVR': ('9C', 2), 'COMPR': ('A0', 2), 'SHIFTL': ('A4', 2), 'SHIFTR': ('A8', 2),
    'RMO': ('AC', 2),

    'CADD': ('BC','4F'),'CSUB': ('8C', '4F'),'CLOAD': ('E4', '4F'),'CSTORE': ('FC', '4F'),
}

REGISTERS = {
    'A': 0, 'X': 1, 'L': 2, 'B': 3, 'S': 4, 'T': 5, 'F': 6, 'PC': 8, 'SW': 9
}

BASE = None
BASE_ADDR = None
LITTAB = {}
MOD_RECORDS = []

def parse_byte_operand(operand):
    if operand.startswith("C'"):
        return len(operand[2:-1])
    if operand.startswith("X'"):
        return len(operand[2:-1]) // 2
    return 1

def read_input_file(filename):
    lines = []
    with open(filename, 'r') as infile, open('intermediate.txt', 'w') as inter:
        for line in infile:
            if line.strip() and not line.lstrip().startswith('.'):
                content = line[6:] if len(line) > 6 else ''
                inter.write(content)
                lines.append(content.rstrip('\n'))
    return lines

def pass1(lines):
    global BASE, BASE_ADDR
    locctr = 0
    symtab, locctr_list = OrderedDict(), []
    literals = []
    progname, start_addr = '', 0

    for line in lines:
        tokens = line.split()
        if not tokens:
            continue
        label, opcode, operand = '', '', ''
        if len(tokens) == 3:
            label, opcode, operand = tokens
        elif len(tokens) == 2:
            opcode, operand = tokens
        elif len(tokens) == 1:
            opcode = tokens[0]

        if opcode == 'START':
            start_addr = int(operand, 16)
            locctr = start_addr
            progname = label
            locctr_list.append((locctr, line))
            continue

        if opcode == 'EQU':
            symtab[label] = locctr
            locctr_list.append((locctr, line))
            continue

        if opcode != 'END':
            locctr_list.append((locctr, line))

        if label and label not in symtab and opcode != 'START':
            symtab[label] = locctr

        if opcode == 'BASE':
            BASE = operand
            BASE_ADDR = symtab.get(operand, 0)
            continue

        if '=' in operand:
            literals.append(operand)

        if opcode == 'LTORG':
            for lit in literals:
                if lit not in LITTAB:
                    LITTAB[lit] = locctr
                    if lit.startswith("=C'"):
                        locctr += len(lit[3:-1])
                    elif lit.startswith("=X'"):
                        locctr += len(lit[3:-1]) // 2
            literals.clear()
            continue

        if opcode == 'END':
            locctr_list.append((locctr, line))
            break

        '''fmt = 3
        if opcode.startswith('+'):
            fmt = 4
        elif opcode in OPTAB:
            fmt = OPTAB[opcode][1]'''
        
        fmt = 3
        if opcode.startswith('+'):
            fmt = 4
        elif opcode in OPTAB:
            f = OPTAB[opcode][1]
            fmt = 4 if f == '4F' else f

        if opcode == 'WORD':
            locctr += 3
        elif opcode == 'RESW':
            locctr += 3 * int(operand)
        elif opcode == 'RESB':
            locctr += int(operand)
        elif opcode == 'BYTE':
            locctr += parse_byte_operand(operand)
        else:
            locctr += fmt

    for lit in literals:
        if lit not in LITTAB:
            LITTAB[lit] = locctr
            if lit.startswith("=C'"):
                locctr += len(lit[3:-1])
            elif lit.startswith("=X'"):
                locctr += len(lit[3:-1]) // 2

    symtab.pop('BASE', None)
    symtab.pop('END', None)

    return locctr_list, symtab, progname, start_addr

def format_object_code(opcode, operand, symtab, curr_addr):
    global MOD_RECORDS

    format4 = opcode.startswith('+')
    op = opcode[1:] if format4 else opcode

    if op not in OPTAB:
        return ''

    code, fmt = OPTAB[op]
    code = int(code, 16)

    if OPTAB[op][1] == '4F':
        reg = 0
        cond = 0
        addr = 0
        parts = []
        if operand:
            parts = [p.strip() for p in operand.split(',')]
            if len(parts) >= 1:
                reg = REGISTERS.get(parts[0], 0)
            if len(parts) >= 2:
                symbol = parts[1]
                addr = symtab.get(symbol, 0)
            if len(parts) == 3:
                cond_map = {'Z': 0b00, 'N': 0b01, 'C': 0b10, 'V': 0b11}
                cond_flag = parts[2].upper()
                if cond_flag in cond_map:
                    cond = cond_map[cond_flag]
                else:
                    raise ValueError(f"Invalid condition flag '{parts[2]}' in operand '{operand}' — must be one of Z, N, C, V.")

        raw_opcode = int(OPTAB[op][0], 16)        # e.g., 0xBC
        opcode_6bit = (raw_opcode >> 2) & 0x3F    # take top 6 bits by shifting right 2 bits

        object_code = (opcode_6bit << 26) | (reg << 22) | (cond << 20) | (addr & 0xFFFFF)

        if len(parts) >= 2 and parts[1] in symtab:
            MOD_RECORDS.append((curr_addr + 1, 5))  # Mod record usually starts after opcode byte

        return f"{object_code:08X}"

    if fmt == 1:
        return f"{code:02X}"

    if fmt == 2:
        regs = operand.split(',') if operand else []
        r1 = REGISTERS.get(regs[0], 0)
        r2 = REGISTERS.get(regs[1], 0) if len(regs) > 1 else 0
        return f"{code:02X}{r1:01X}{r2:01X}"

    n, i, x, b, p, e = 1, 1, 0, 0, 0, 1 if format4 else 0
    disp = 0
    address = 0

    if operand:
        if ',X' in operand:
            x = 1
            operand = operand.replace(',X', '')

        if operand.startswith('#'):
            n, i = 0, 1
            operand = operand[1:]
            if operand.isdigit():
                disp = int(operand)
            else:
                address = symtab.get(operand, 0)
        elif operand.startswith('@'):
            n, i = 1, 0
            operand = operand[1:]
            address = symtab.get(operand, 0)
        else:
            address = symtab.get(operand, 0)

        if not operand.isdigit():
            if not format4:
                relative_disp = address - (curr_addr + 3)
                if -2048 <= relative_disp <= 2047:
                    p = 1
                    disp = relative_disp & 0xFFF
                elif BASE_ADDR is not None:
                    b = 1
                    disp = (address - BASE_ADDR) & 0xFFF
            else:
                e = 1
                disp = address & 0xFFFFF
                if operand in symtab:
                    MOD_RECORDS.append((curr_addr + 1, 5))

    ni = (n << 1) | i
    opcode_with_ni = (code & 0xFC) | ni
    xbpe = (x << 3) | (b << 2) | (p << 1) | e

    if format4:
        return f"{opcode_with_ni:02X}{xbpe:01X}{disp:05X}"
    return f"{opcode_with_ni:02X}{xbpe:01X}{disp:03X}"

def pass2(locctr_list, symtab):
    results = []
    for loc, line in locctr_list:
        tokens = line.split()
        label, opcode, operand = '', '', ''
        if len(tokens) == 3:
            label, opcode, operand = tokens
        elif len(tokens) == 2:
            opcode, operand = tokens
        elif len(tokens) == 1:
            opcode = tokens[0]

        obj = ''
        if opcode == 'WORD':
            obj = f"{int(operand):06X}"
        elif opcode == 'BYTE':
            if operand.startswith("C'"):
                obj = ''.join(f"{ord(c):02X}" for c in operand[2:-1])
            elif operand.startswith("X'"):
                obj = operand[2:-1]
        elif opcode in ['RESW', 'RESB', 'START', 'END', 'EQU', 'LTORG', 'BASE']:
            obj = ''
        else:
            obj = format_object_code(opcode, operand, symtab, loc)

        results.append((loc, line, obj))

    for lit, addr in LITTAB.items():
        if lit.startswith("=C'"):
            val = ''.join(f"{ord(c):02X}" for c in lit[3:-1])
        elif lit.startswith("=X'"):
            val = lit[3:-1]
        else:
            val = '00'
        results.append((addr, lit, val))

    return results

def write_outputs(p1, p2, symtab, progname, start_addr):
    progname = progname.ljust(6, 'X')
    symtab = OrderedDict((k, v) for k, v in symtab.items() if k.upper() not in {'END', 'BASE'})

    with open("out_pass1.txt", 'w') as f:
        for loc, line in p1:
            tokens = line.split()
            label, opcode, operand = '', '', ''
            if len(tokens) == 3:
                label, opcode, operand = tokens
            elif len(tokens) == 2:
                opcode, operand = tokens
            elif len(tokens) == 1:
                opcode = tokens[0]
            f.write(f"{loc:04X}  {label:<8}{opcode:<8}{operand:<10}\n")

    with open("symbTable.txt", 'w') as f:
        for sym, addr in symtab.items():
            f.write(f"{sym:<10} {addr:04X}\n")

    with open("out_pass2.txt", 'w') as f:
        for loc, line, obj in p2:
            tokens = line.split()
            label, opcode, operand = '', '', ''
            if len(tokens) == 3:
                label, opcode, operand = tokens
            elif len(tokens) == 2:
                opcode, operand = tokens
            elif len(tokens) == 1:
                opcode = tokens[0]
            f.write(f"{loc:04X}  {label:<8}{opcode:<8}{operand:<10}{obj}\n")

    end_loc = None
    for loc, line, obj in p2:
        tokens = line.strip().split()
        if len(tokens) >= 2 and tokens[0] == 'END':
            end_loc = loc

    prog_len = end_loc - start_addr

    # account for literals placed after END (i.e. no LTORG before END was hit)
    for lit, addr in LITTAB.items():
        if lit.startswith("=C'"):
            lit_len = len(lit[3:-1])
        elif lit.startswith("=X'"):
            lit_len = len(lit[3:-1]) // 2
        else:
            lit_len = 1
        lit_end = addr + lit_len
        if lit_end - start_addr > prog_len:
            prog_len = lit_end - start_addr

    with open("HTME.txt", 'w') as f:
        # prog_len = p2[-1][0] + 3 - start_addr
        f.write(f"H^{progname}^{start_addr:06X}^{prog_len:06X}\n")

        record = ''
        record_start = None
        for loc, line, obj in p2:
            if line.strip().startswith('='):
                continue
            tokens = line.split()
            opcode = tokens[1] if len(tokens) > 1 else ''
            if opcode in ['RESW', 'RESB']:
                if record:
                    f.write(f"T^{record_start:06X}^{len(record) // 2:02X}^{record}\n")
                    record = ''
                    record_start = None
            elif obj:
                if record_start is None:
                    record_start = loc
                if len(record + obj) > 60:
                    f.write(f"T^{record_start:06X}^{len(record) // 2:02X}^{record}\n")
                    record = obj
                    record_start = loc
                else:
                    record += obj

        if record:
            f.write(f"T^{record_start:06X}^{len(record) // 2:02X}^{record}\n")

        for addr, length in MOD_RECORDS:
            f.write(f"M^{addr:06X}^{length:02X}\n")

        f.write(f"E^{start_addr:06X}\n")

def main():
    if len(sys.argv) < 3 or sys.argv[1] != '--data':
        print("Usage: python3 assembler221000693.py --data in.txt")
        return
    lines = read_input_file(sys.argv[2])
    p1, symtab, progname, start = pass1(lines)
    p2 = pass2(p1, symtab)
    write_outputs(p1, p2, symtab, progname, start)
    print("Assembly complete. Outputs: intermediate.txt, out_pass1.txt, symbTable.txt, out_pass2.txt, HTME.txt")

if __name__ == '__main__':
    main()
