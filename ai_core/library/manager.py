import os

class FootprintManager:
    """
    Digital Warehouse for NeuroBoard.
    Stores S-expression strings for instant injection into the KiCad canvas.
    """
    def __init__(self):
        # A simple dictionary to store raw S-expressions for our standard parts.
        self.library = {
            "C_0402_100nF": self._get_c_0402_sexpr()
        }

    def get_footprint_string(self, part_name: str) -> str:
        return self.library.get(part_name, "")

    def _get_c_0402_sexpr(self) -> str:
        # Minimal valid KiCad 8/10 S-expression for an 0402 Capacitor
        return """(footprint "Capacitor_SMD:C_0402_1005Metric"
  (layer "F.Cu")
  (tedit 5F68FEEF)
  (descr "Capacitor SMD 0402 (1005 Metric), square (rectangular) end terminal, IPC_7351 nominal, (Body size source: IPC-SM-782 page 76, https://www.pcb-3d.com/wordpress/wp-content/uploads/ipc-sm-782a_amendment_1_and_2.pdf), generated with kicad-footprint-generator")
  (tags "capacitor")
  (attr smd)
  (fp_text reference "REF**" (at 0 -1.16) (layer "F.SilkS")
    (effects (font (size 1 1) (thickness 0.15)))
  )
  (fp_text value "100nF" (at 0 1.16) (layer "F.Fab")
    (effects (font (size 1 1) (thickness 0.15)))
  )
  (fp_line (start -0.106252 0.36) (end 0.106252 0.36) (layer "F.SilkS") (width 0.12))
  (fp_line (start -0.106252 -0.36) (end 0.106252 -0.36) (layer "F.SilkS") (width 0.12))
  (fp_rect (start -0.93 -0.68) (end 0.93 0.68) (layer "F.CrtYd") (width 0.05))
  (fp_line (start -0.5 0.25) (end -0.5 -0.25) (layer "F.Fab") (width 0.1))
  (fp_line (start -0.5 -0.25) (end 0.5 -0.25) (layer "F.Fab") (width 0.1))
  (fp_line (start 0.5 -0.25) (end 0.5 0.25) (layer "F.Fab") (width 0.1))
  (fp_line (start 0.5 0.25) (end -0.5 0.25) (layer "F.Fab") (width 0.1))
  (pad "1" smd roundrect (at -0.48 0) (size 0.6 0.86) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
  (pad "2" smd roundrect (at 0.48 0) (size 0.6 0.86) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25))
)"""
