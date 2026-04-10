import os
# We must use kipy, as pip install kicad-python provides kipy.
from kipy.kicad import KiCad

def ping_kicad():
    try:
        # Connect to the industrial-grade api.sock
        kicad = KiCad(socket_path="ipc:///C:/Users/Bibek/AppData/Local/Temp/kicad/api.sock")
        
        print("Connecting to KiCad 10 Native IPC...")
        board = kicad.get_board()
        
        project_name = board.name if board.name else "Unknown/Unsaved"
        if '\\' in project_name or '/' in project_name:
            project_name = os.path.basename(project_name)

        # Count pads
        pads = board.get_pads()
        pad_count = len(pads)
        
        print(f"Ping Successful!")
        print(f"Open Project: {project_name}")
        print(f"Total Pads: {pad_count}")
        
    except Exception as e:
        print(f"Ping Failed: {e}")

if __name__ == "__main__":
    ping_kicad()
