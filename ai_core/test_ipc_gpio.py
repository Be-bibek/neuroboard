import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from system.ipc_kicad import KiCadIPC

def main():
    print("--- NeuroBoard IPC GPIO Placement Test ---")
    
    ipc = KiCadIPC()
    
    print("\n[Step 1] Creating Net dependencies...")
    ipc.create_net("3V3")
    ipc.create_net("5V")
    ipc.create_net("GND")
    
    print("\n[Step 2] Placing GPIO Header (40-Pin RPi Header)...")
    # For a standard Raspberry pi header
    component_id = "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"
    ref_des = "J1_GPIO"
    
    # Place at (x=20mm, y=20mm)
    res = ipc.place_component(component_id, ref_des, x=20.0, y=20.0)
    
    if res:
        print(f"\n[OK] Result: {res}")
        print("\n[OK] Success! The GPIO Header has been placed programmatically.")
    else:
        print("\n[FAILED] Failed to place the GPIO footprint. Is the local layout server running on port 3000?")

if __name__ == "__main__":
    main()
