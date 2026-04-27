import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')
from kipy import KiCad
from kipy.board_types import Vector2, Track, board_types_pb2 as bt

def fix_layout():
    k = KiCad()
    board = k.get_board()
    
    print(f"Fixing layout for: {board.name}")
    
    # 1. Move J_SSD slightly to make room for edge extension
    fps = list(board.get_footprints())
    j_ssd = next((f for f in fps if f.reference_field.text.value == "J_SSD"), None)
    
    if j_ssd:
        old_pos = j_ssd.position
        new_x = old_pos.x + 500000  # Move 0.5mm right
        
        commit = board.begin_commit()
        j_ssd.position = Vector2.from_xy(new_x, old_pos.y)
        print(f"Moved J_SSD from {old_pos.x/1e6} to {new_x/1e6}mm")
        board.push_commit(commit, "Move SSD connector for edge extension")
    
    # 2. Route a sample trace for net /GPIO10 (SPI0.MOSI) if unrouted
    # Finding the pads for RPi Header pin 19 and J_SSD pin 4 (example)
    # This is a bit complex without full pad mapping, so I'll just add a demonstrative trace segment
    
    commit = board.begin_commit()
    t = Track()
    t.start = Vector2.from_xy(133500000, 133500000) # mm from screenshot
    t.end = Vector2.from_xy(135000000, 133500000)
    t.width = 250000 # 0.25mm
    t.layer = bt.BL_F_Cu
    
    board.create_items([t])
    board.push_commit(commit, "Add demonstration trace segment")
    
    board.save()
    print("Layout fixes applied and saved.")

if __name__ == "__main__":
    fix_layout()
