import unittest
import sys

sys.path.insert(0, r"C:\Users\Bibek\NeuroBoard")
from ai_core.system.ipc_client import IPCClient
from ai_core.si.sparameter_analysis import SParameterAnalysis
from ai_core.power_integrity.pdn_simulator import PDNSimulator
from ai_core.integration.freerouting import FreeroutingIntegration

class TestNeuroBoardIntegrations(unittest.TestCase):
    
    def setUp(self):
        self.ipc = IPCClient()
        self.si = SParameterAnalysis()
        self.pdn = PDNSimulator()
        self.freerouting = FreeroutingIntegration()

    def test_ipc_connectivity(self):
        """ Tests if the IPC Client successfully resolves the session """
        self.ipc.connect()
        state = self.ipc.get_board_state()
        self.assertIn("layer_count", state)
        self.assertIn("footprints", state)
        self.assertTrue(len(state["footprints"]) > 0, "No footprints detected via IPC.")

    def test_sparameter_simulation(self):
        """ Tests the deterministic S-Parameter logic feedback """
        res = self.si.simulate_differential_pair(length_mm=45.0, frequency_ghz=5.0)
        self.assertIn("status", res)
        if res["status"] != "disabled":
            self.assertGreater(res["target_z_diff"], 0)
            self.assertIn("simulated_z_diff", res)

    def test_pdn_simulation(self):
        """ Tests PySpice PDN wrapper logic """
        res = self.pdn.analyze_power_rail("3.3V_SYS", 3.3, 2.0, 0.05)
        self.assertIn("status", res)
        if res["status"] != "disabled":
            self.assertAlmostEqual(res["ir_drop_v"], 0.1)

    def test_freerouting_benchmark_fallback(self):
        """ Verifies that Freerouting generates expected failures if DSN doesn't exist """
        res = self.freerouting.execute_fallback_route("invalid.kicad_pcb")
        # Should gracefully return error if enabled, else 'disabled'
        self.assertIn(res["status"], ["error", "disabled", "failed"])

if __name__ == '__main__':
    unittest.main()
