import sys, os, re

BOARD_PATH = r"C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb"

def get_origin():
    # Attempt Headless pcbnew load
    try:
        import pcbnew
        board = pcbnew.LoadBoard(BOARD_PATH)
        if board is not None:
            aux = board.GetDesignSettings().GetAuxOrigin()
            return pcbnew.ToMM(aux.x), pcbnew.ToMM(aux.y)
    except Exception as e:
        pass
        
    # Fallback to Regex
    try:
        with open(BOARD_PATH, 'r', encoding='utf-8') as f:
            text = f.read()
        m = re.search(r'\(aux_axis_origin\s+([\-\d.]+)\s+([\-\d.]+)\)', text)
        if m:
            return float(m.group(1)), float(m.group(2))
    except:
        pass
    return None, None

ox, oy = get_origin()
if ox is not None:
    print(f"Origin X: {ox}, Origin Y: {oy}")
else:
    print("Could not locate origin")
