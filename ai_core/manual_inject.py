
from kipy import KiCad
import os
import sys

pcb_path = r'C:\Users\Bibek\Documents\pi-hat\PiHAT-KiCAD-Pro-Legacy\PiHAT-KiCAD-Pro-Legacy.kicad_pcb'

def inject():
    try:
        # 1. Cleanup via API
        try:
            k = KiCad()
            board = k.get_board()
            to_delete = []
            for fp in board.get_footprints():
                try:
                    ref = fp.reference_field.text.value
                    if not ref: ref = fp.reference_field.text.text.text.text
                    if ref and ref.startswith('C_DEC_'):
                        to_delete.append(fp)
                except: continue
            
            if to_delete:
                commit = board.begin_commit()
                board.remove_items(to_delete)
                board.push_commit(commit)
                board.save()
                print(f'CLEANUP: Removed {len(to_delete)} items.')
        except Exception as e:
            print(f'API CLEANUP FAILED (maybe already gone): {e}')

        # 2. Direct File Edit
        if not os.path.exists(pcb_path):
            print(f'FILE NOT FOUND: {pcb_path}')
            return

        with open(pcb_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.strip()
        if content.endswith(')'):
            content = content[:-1] # Remove last )
        
        new_fps = '\n'
        for i in range(1, 5):
            ref = f'C_DEC_{i}'
            x = 113.5 + (i * 1.5)
            y = 66.5
            sexp = f"""
  (footprint "Device:C_0402_1005Metric" (layer "F.Cu")
    (at {x} {y} 90)
    (property "Reference" "{ref}" (at 0 -1.5 90) (effects (font (size 1 1) (thickness 0.15))))
    (property "Value" "100nF" (at 0 1.5 90) (effects (font (size 1 1) (thickness 0.15))))
    (fp_line (start -0.5 -0.25) (end 0.5 -0.25) (layer "F.Fab") (width 0.1))
    (fp_line (start 0.5 -0.25) (end 0.5 0.25) (layer "F.Fab") (width 0.1))
    (fp_line (start 0.5 0.25) (end -0.5 0.25) (layer "F.Fab") (width 0.1))
    (fp_line (start -0.5 0.25) (end -0.5 -0.25) (layer "F.Fab") (width 0.1))
    (pad "1" smd roundrect (at -0.45 0 90) (size 0.5 0.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
    (pad "2" smd roundrect (at 0.45 0 90) (size 0.5 0.5) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
  )
"""
            new_fps += sexp
        
        content += new_fps + '\n)'
        
        with open(pcb_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print('SUCCESS: Manually injected 4 real S-expression footprints.')
    except Exception as e:
        print(f'FATAL ERROR: {e}')

if __name__ == '__main__':
    inject()
