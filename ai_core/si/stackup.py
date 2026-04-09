class StackupModel:
    def __init__(self, layer_name, dielectric_height_h, copper_thickness_t, dielectric_er):
        self.layer_name = layer_name
        self.h = dielectric_height_h  # mm
        self.t = copper_thickness_t   # mm
        self.er = dielectric_er       # Relative permittivity

    @classmethod
    def get_jlcpcb_4layer_standard(cls):
        """
        Returns a roughly standard JLC04161H-3313 stackup.
        L1 (F.Cu) is separated from L2 (In1.Cu - usually GND) by a Prepreg layer.
        """
        # Outer layer (F.Cu/B.Cu)
        f_cu = cls('F.Cu', dielectric_height_h=0.1, copper_thickness_t=0.035, dielectric_er=4.3)
        b_cu = cls('B.Cu', dielectric_height_h=0.1, copper_thickness_t=0.035, dielectric_er=4.3)
        return {'F.Cu': f_cu, 'B.Cu': b_cu}
