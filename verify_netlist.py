import sys
from ai_core.netlist.netlist_manager import NetlistManager
from ai_core.constraints.constraint_manager import ConstraintManager
from ai_core.system.ipc_client import IPCClient

def verify_system():
    # 1. Constraint Manager
    cm = ConstraintManager("config/stackup.yaml")
    print(f"Stackup Layers: {cm.get_layer_count()}")
    print(f"Differential Target Impedance: {cm.diff_impedance_target} ohms")
    
    # 2. Netlist Manager
    nm = NetlistManager("pi_hat.net")
    pairs = nm.get_routing_pairs()
    print(f"Detected Diff Pairs: {pairs}")
    
    # Check PCIe Nets
    has_tx_p = "PCIE_TX_P" in nm.nets
    print(f"PCIE_TX_P net exists: {has_tx_p}")

if __name__ == "__main__":
    verify_system()
