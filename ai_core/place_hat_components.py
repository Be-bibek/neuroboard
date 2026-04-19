"""
place_hat_components.py  — KiCad 10 IPC Edition
=================================================
Connects to the running KiCad 10 PCB Editor via the official kipy IPC API
and places the following components inside the PiHAT board:

  J2  — FPC Hirose 16-pin 0.5mm (PCIe socket)       → 113mm, 70mm
  J3  — M.2 M-Key 2242 NVMe slot                    → 135mm, 74mm
  D1  — LED 0603 1608Metric (status indicator)       → 112mm, 88mm
  R1  — 100Ω resistor 0402 (LED current limit)       → 112mm, 92mm
  C1  — 100nF cap 0402 (decoupling)                  → 120mm, 88mm
  C2  — 10uF  cap 0805 (bulk bypass)                 → 120mm, 93mm
"""

from kipy import KiCad
from kipy.board import FootprintInstance, BoardLayer, board_types_pb2 as bt

# ── KiCad internal units ──────────────────────────────────────────────────
# KiCad 10 stores positions in nanometres. 1 mm = 1 000 000 nm.
NM_PER_MM = 1_000_000

def mm(v: float) -> int:
    return int(v * NM_PER_MM)

def make_fp(library: str, entry: str, ref: str, value: str,
            x_mm: float, y_mm: float,
            rot_deg: float = 0.0,
            back: bool = False) -> FootprintInstance:
    """
    Build a FootprintInstance proto message for create_items().

    Args:
        library   – KiCad library nickname (e.g. 'Connector_M.2')
        entry     – Footprint name inside that library
        ref       – Reference designator (J2, D1, …)
        value     – Value field text
        x_mm, y_mm – Position in mm relative to board origin
        rot_deg   – Rotation in degrees (counter-clockwise positive)
        back      – If True, place on B.Cu; otherwise F.Cu
    """
    p = bt.FootprintInstance()

    # Library identity
    p.definition.id.library_nickname = library
    p.definition.id.entry_name       = entry

    # Position (nanometres)
    p.position.x_nm = mm(x_mm)
    p.position.y_nm = mm(y_mm)

    # Orientation — KiCad Angle proto uses value_degrees (float)
    p.orientation.value_degrees = float(rot_deg)

    # Layer
    p.layer = BoardLayer.Value("BL_B_Cu") if back else BoardLayer.Value("BL_F_Cu")

    # Reference and value text fields
    p.reference_field.text.text.text = ref
    p.value_field.text.text.text     = value

    return FootprintInstance(proto=p)


def main():
    print("=" * 60)
    print("NeuroBoard — KiCad 10 IPC Placement Engine")
    print("=" * 60)

    # Connect
    kicad = KiCad()
    print("[IPC] KiCad version:", kicad.get_version())

    board = kicad.get_board()
    print("[IPC] Board:", board.name)

    # Show existing footprints for context
    existing = board.get_footprints()
    print()
    print("[INFO] Existing footprints on board:")
    for fp in existing:
        ref  = str(fp.reference_field.text)
        lib  = str(fp.definition.id)
        x    = fp.position.x / NM_PER_MM
        y    = fp.position.y / NM_PER_MM
        print("  " + ref + "  |  " + lib + "  @  (" + str(round(x,2)) + ", " + str(round(y,2)) + ") mm")

    print()

    # ── Placement table ───────────────────────────────────────────────────
    # Board outline (from existing mounting holes):
    #   TL: (103.5, 47.5)  TR: (161.5, 47.5)
    #   BL: (103.5, 96.5)  BR: (161.5, 96.5)
    # Centre: (132.5, 72.0)
    # J1 GPIO header: (108.37, 48.77) — top-left
    #
    # Target layout inspired by RPi M.2 HAT+ reference design:
    #   J2  PCIe FPC socket   — left-centre area
    #   J3  M.2 NVMe slot     — centre of board
    #   D1  Status LED        — lower-left
    #   R1  LED resistor      — below D1
    #   C1  100nF bypass cap  — near J3 power pins
    #   C2  10uF bulk cap     — near J3 power pins

    components = [
        # library,                    entry,                            ref,  value,           x_mm,   y_mm,  rot
        ("Connector_FFC-FPC",        "Hirose_FH12-16S-0.5SH_1x16",   "J2", "PCIe_FPC_16P",  113.5,  70.0,  90.0),
        ("Connector_M.2",            "M.2_M-Key_2230-2242-2260-2280", "J3", "NVMe_M.2_2242", 135.0,  74.0,   0.0),
        ("LED_SMD",                  "LED_0603_1608Metric",           "D1", "PWR_LED",        112.0,  88.0,   0.0),
        ("Device",                   "R_0402_1005Metric",             "R1", "100R",           112.0,  92.0,   0.0),
        ("Device",                   "C_0402_1005Metric",             "C1", "100nF",          120.0,  88.0,   0.0),
        ("Device",                   "C_0805_2012Metric",             "C2", "10uF",           120.0,  93.0,   0.0),
    ]

    footprints = []
    for lib, entry, ref, value, x, y, rot in components:
        print("[PLACE] " + ref + " (" + lib + ":" + entry + ")  @  (" + str(x) + ", " + str(y) + ") mm  rot=" + str(rot) + "°")
        fp = make_fp(lib, entry, ref, value, x, y, rot)
        footprints.append(fp)

    print()
    print("[IPC] Committing " + str(len(footprints)) + " footprints to board...")

    # Open transaction
    commit = board.begin_commit()

    # Insert footprints
    created = board.create_items(footprints)

    # Commit
    board.push_commit(commit)

    print("[IPC] Saving board to disk...")
    board.save()

    print()
    print("[OK] SUCCESS — " + str(len(created)) + " components placed.")
    print()
    for (_, _, ref, _, x, y, _), c in zip(components, created):
        print("  + " + ref + "  placed  (KIID=" + str(c.id) + ")")
    print()
    print("-> Refresh KiCad PCB Editor (press R or use View > Refresh) to see changes.")


if __name__ == "__main__":
    main()
