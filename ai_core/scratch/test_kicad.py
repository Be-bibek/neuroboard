import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')
from kipy import KiCad
board = KiCad().get_board()
print("dir board:", dir(board))
for fp in board.get_footprints()[:1]:
    print("dir fp:", dir(fp))
