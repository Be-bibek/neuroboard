"""
move_hat_components.py
======================
Uses KiCad 10 IPC (kipy) to reposition previously placed components
into their physically accurate locations complementing a Raspberry Pi M.2 HAT+.
"""

from kipy import KiCad

# Conversions
NM_PER_MM = 1_000_000

def mm(v: float) -> int:
    return int(v * NM_PER_MM)

def main():
    print("=" * 60)
    print("NeuroBoard — Repositioning Engine")
    print("=" * 60)

    # 1. Connect
    kicad = KiCad()
    board = kicad.get_board()
    print("[IPC] Connected to specific board:", board.name)

    # 2. Target Locations Dictionary
    # Reference frame:
    # Top-Left edge ~ (100, 44) mm
    # Bottom-Right edge ~ (165, 100) mm
    # J1 GPIO header is at top edge
    targets = {
        # J2 - FPC PCIe connector at the bottom left, opening leftwards
        "J2": {"x": 105.0, "y": 80.0, "rot": 90.0},
        
        # J3 - M.2 NVMe Slot near the center, card extends right to 157mm
        "J3": {"x": 115.0, "y": 70.0, "rot": 0.0},
        
        # D1, R1 - Status LED & resistor at bottom left corner below J2
        "D1": {"x": 104.0, "y": 92.0, "rot": 0.0},
        "R1": {"x": 107.0, "y": 92.0, "rot": 0.0},
        
        # C1, C2 - Decoupling caps near the M.2 power pins
        "C1": {"x": 112.0, "y": 64.0, "rot": 90.0},
        "C2": {"x": 112.0, "y": 66.0, "rot": 90.0},
    }

    # 3. Locate & modify items
    footprints_to_update = []
    
    for fp in board.get_footprints():
        try:
            ref = fp.reference_field.text.value
        except AttributeError:
            continue
            
        if ref in targets:
            spec = targets[ref]
            print(f"[REPOSITION] Moving {ref} to ({spec['x']} mm, {spec['y']} mm) @ {spec['rot']}°")
            
            # Mutate underlying proto structure
            fp.proto.position.x_nm = mm(spec["x"])
            fp.proto.position.y_nm = mm(spec["y"])
            fp.proto.orientation.value_degrees = float(spec["rot"])
            
            footprints_to_update.append(fp)

    # 4. Push updates to KiCad
    commit = board.begin_commit()
    
    if footprints_to_update:
        print(f"\n[IPC] Sending update to {len(footprints_to_update)} footprint(s)...")
        board.update_items(footprints_to_update)
        board.push_commit(commit)
        board.save()
        print("[OK] Layout updated and saved. Please refresh KiCad!")
    else:
        board.drop_commit(commit)
        print("[WARN] No target footprints found to update.")

if __name__ == "__main__":
    main()
