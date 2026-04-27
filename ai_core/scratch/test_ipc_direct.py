import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')
from kipy import KiCad

def test_ipc():
    try:
        k = KiCad()
        b = k.get_board()
        print(f"Board name: {b.name}")
        print(f"Nets: {len(list(b.get_nets()))}")
    except Exception as e:
        print(f"IPC Error: {e}")

if __name__ == "__main__":
    test_ipc()
