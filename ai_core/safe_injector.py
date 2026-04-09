import sys, os, re

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
LIB_DIR    = r'C:\Users\Bibek\NeuroBoard\lib\footprint'

def get_fp(name):
    for f in os.listdir(LIB_DIR):
        if name in f and f.endswith('.kicad_mod'):
            with open(os.path.join(LIB_DIR, f), 'r') as file:
                return file.read()
    return None

fpc_fp = get_fp('C2935243') or get_fp('FPC')
m2_fp = get_fp('APCI0107') or get_fp('C841661')

if not fpc_fp or not m2_fp:
    print("Error: Missing footprint files")
    sys.exit(1)

# Format the footprints for placement
def format_fp(content, ref, val, x, y):
    fp_mod = re.sub(
        r'\(at\s+[\-\d.]+\s+[\-\d.]+(?:\s+[\-\d.]+)?\)',
        '(at %s %s)' % (x, y),
        content, count=1
    )
    fp_mod = re.sub(
        r'(\(property\s+"Reference"\s+)"[^"]*"',
        r'\1"%s"' % ref, fp_mod, count=1
    )
    fp_mod = re.sub(
        r'(\(property\s+"Value"\s+)"[^"]*"',
        r'\1"%s"' % val, fp_mod, count=1
    )
    fp_mod = fp_mod.replace('(module ', '(footprint ')
    return '\n  ' + fp_mod.strip().replace('\n', '\n  ') + '\n'

j1_str = format_fp(fpc_fp, 'J1', 'FPC_16P_PCIe', 110.0, 120.0)
j2_str = format_fp(m2_fp, 'J2', 'M2_Key-M_Hailo8', 125.0, 85.0)

with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    board_str = f.read()

# Make sure we don't duplicate
if "(property \"Reference\" \"J1\")" in board_str or "(property \"Reference\" \"J2\")" in board_str:
    print("Found existing J1/J2, removing them is complex, assuming clean board...")

# Strip the trailing whitespace and closing paren
board_str = board_str.rstrip()
if board_str.endswith(')'):
    board_str = board_str[:-1].rstrip()

board_str = board_str + "\n" + j1_str + "\n" + j2_str + "\n)\n"

with open(BOARD_PATH, 'w', encoding='utf-8') as f:
    f.write(board_str)

print("Safely injected J1 and J2 footprints strings at the end of the file.")
