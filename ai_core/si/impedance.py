import math

class ImpedanceCalculator:
    def __init__(self, stackup):
        self.stackup = stackup

    def calc_z0_microstrip(self, w):
        """
        Calculates Surface Microstrip Single-Ended Impedance (Z0)
        Equations from IPC-2141.
        w = trace width, h = dielectric height, t = trace thickness
        """
        h = self.stackup.h
        t = self.stackup.t
        er = self.stackup.er
        
        # Effective dielectric constant
        er_eff = (er + 1)/2 + (er - 1)/2 * (1 + 10 * h / w)**-0.5
        
        # Single ended impedance
        Z0 = 87.0 / math.sqrt(er + 1.41) * math.log(5.98 * h / (0.8 * w + t))
        return Z0

    def calc_zdiff_microstrip(self, w, s):
        """
        Calculates Edge-Coupled Surface Microstrip Differential Impedance (Zdiff)
        w = trace width, s = trace spacing
        """
        Z0 = self.calc_z0_microstrip(w)
        h = self.stackup.h
        
        # Coupling factor k (rough approximation)
        Zdiff = 2 * Z0 * (1 - 0.48 * math.exp(-0.96 * s / h))
        return Zdiff
        
    def get_optimal_geometry(self, target_zdiff=100.0, layer='F.Cu'):
        """
        Scans combinations of width and spacing to find the combination
        closest to the target differential impedance.
        """
        best_w, best_s = 0.15, 0.15
        best_error = float('inf')
        
        # JLC constraints usually min w=0.09, min s=0.09
        widths = [w/1000.0 for w in range(100, 250, 10)] # 0.10 to 0.25mm
        spacings = [s/1000.0 for s in range(100, 300, 10)] # 0.10 to 0.30mm
        
        for w in widths:
            for s in spacings:
                zdiff = self.calc_zdiff_microstrip(w, s)
                err = abs(zdiff - target_zdiff)
                if err < best_error:
                    best_error = err
                    best_w = w
                    best_s = s
                    
        return best_w, best_s, best_error
