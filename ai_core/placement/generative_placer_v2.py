"""
ai_core/placement/generative_placer_v2.py
===========================================
Phase 9: Staged Smart Placement Engine (Force-Directed)

Integrates NetworkX for topological clustering and a custom vector-based
physics engine for multi-objective optimization.

Logic:
  1. Build Netlist Graph (NetworkX)
  2. Cluster components using Community Detection
  3. Run Force-Directed Simulation:
     - Attractive (Spring) forces from nets
     - Repulsive (Electrostatic) forces from components/edges
     - Static anchors for mechanical features
"""

from __future__ import annotations

import os
import re
import logging
import random
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional

log = logging.getLogger("SystemLogger")

class GenerativePlacerV2:
    """
    Advanced placement engine using Force-Directed Graphs and Clustering.
    """

    def __init__(self, board_width: float = 100.0, board_height: float = 100.0):
        self.width  = board_width
        self.height = board_height
        self.graph  = nx.Graph()
        self.nodes: Dict[str, Dict] = {} # ref -> {pos, fixed, mass, cluster}
        self.clusters: Dict[int, List[str]] = {}

    def load_from_netlist(self, netlist_path: str, placement_meta: List[Dict] = None):
        """
        Parse a KiCad .net file into a NetworkX graph.
        """
        if not os.path.exists(netlist_path):
            log.error(f"[PlacerV2] Netlist not found: {netlist_path}")
            return

        with open(netlist_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Extract connectivity
        # Pattern: (net (code 1) (name "GND") (node (ref "J1") (pin "6")) ...)
        net_blocks = re.findall(r'\(net \(code \d+\) \(name "([^"]+)"\)\s*(.*?)\)\s*(?=\(net|\)\s*$)', content, re.DOTALL)
        
        for net_name, nodes_blob in net_blocks:
            # Skip high-fanout power nets for clustering (they would flatten the graph)
            if net_name.upper() in ("GND", "VCC", "+3V3", "+5V", "3V3", "5V"):
                continue

            refs = re.findall(r'\(node \(ref "([^"]+)"\)', nodes_blob)
            # Create edges between all components on the same net (clique)
            for i in range(len(refs)):
                for j in range(i + 1, len(refs)):
                    # Edge weight can be increased for critical high-speed nets
                    weight = 10.0 if any(k in net_name.upper() for k in ("PCIE", "SD_", "DAT")) else 1.0
                    if self.graph.has_edge(refs[i], refs[j]):
                        self.graph[refs[i]][refs[j]]['weight'] += weight
                    else:
                        self.graph.add_edge(refs[i], refs[j], weight=weight)

        # 2. Enrich with metadata (anchors, thermal hints)
        meta_lookup = {item["module"]: item["metadata"] for item in (placement_meta or [])}
        
        # Initialize node states
        for ref in self.graph.nodes:
            self.nodes[ref] = {
                "pos":   np.array([random.uniform(0, self.width), random.uniform(0, self.height)]),
                "fixed": False,
                "mass":  1.0,
                "meta":  {},
            }
            # Match ref to module metadata
            for mod_name, meta in meta_lookup.items():
                if mod_name in ref:
                    self.nodes[ref]["meta"] = meta
                    if meta.get("thermal_class") == "high":
                        self.nodes[ref]["mass"] = 2.0
                    break

    def set_anchor(self, ref: str, x: float, y: float):
        """Lock a component at a specific coordinate."""
        if ref in self.nodes:
            self.nodes[ref]["pos"]   = np.array([x, y])
            self.nodes[ref]["fixed"] = True
            log.debug(f"[PlacerV2] Anchored {ref} at ({x}, {y})")

    def run(self, iterations: int = 200, learning_rate: float = 0.5):
        """
        Force-Directed Simulation Loop.
        """
        log.info(f"[PlacerV2] Starting physics solver ({iterations} iterations)...")
        
        # 1. Communities (Topological Clustering)
        communities = nx.community.louvain_communities(self.graph)
        for i, comm in enumerate(communities):
            self.clusters[i] = list(comm)
            for ref in comm:
                if ref in self.nodes:
                    self.nodes[ref]["cluster"] = i

        # 2. Simulation Loop
        for i in range(iterations):
            # Annealing learning rate
            k = learning_rate * (1.0 - i / iterations)
            
            # Reset forces
            forces = {ref: np.zeros(2) for ref in self.nodes}

            # A. Attractive Forces (Springs)
            for u, v, data in self.graph.edges(data=True):
                w = data.get("weight", 1.0)
                pos_u = self.nodes[u]["pos"]
                pos_v = self.nodes[v]["pos"]
                diff  = pos_v - pos_u
                dist  = np.linalg.norm(diff) + 1e-6
                
                # F = k * log(d/l) or similar
                # We use a simple linear spring F = d * w
                force = (diff / dist) * dist * (w * 0.05)
                forces[u] += force
                forces[v] -= force

            # B. Repulsive Forces (Anti-collision)
            refs = list(self.nodes.keys())
            for idx_a in range(len(refs)):
                for idx_b in range(idx_a + 1, len(refs)):
                    u, v = refs[idx_a], refs[idx_b]
                    pos_u = self.nodes[u]["pos"]
                    pos_v = self.nodes[v]["pos"]
                    diff  = pos_u - pos_v
                    dist  = np.linalg.norm(diff) + 1e-6
                    
                    if dist < 20.0: # Interaction radius
                        # F = c / d^2
                        force = (diff / dist) * (50.0 / (dist**2))
                        forces[u] += force
                        forces[v] -= force

            # C. Edge/Boundary Repulsion
            for ref, state in self.nodes.items():
                pos = state["pos"]
                # Repel from X=0, Y=0, X=W, Y=H
                forces[ref][0] += 10.0 / (pos[0] + 1e-6)**2
                forces[ref][1] += 10.0 / (pos[1] + 1e-6)**2
                forces[ref][0] -= 10.0 / (self.width - pos[0] + 1e-6)**2
                forces[ref][1] -= 10.0 / (self.height - pos[1] + 1e-6)**2

            # Apply Forces
            for ref, force in forces.items():
                if not self.nodes[ref]["fixed"]:
                    # Limit displacement
                    mag = np.linalg.norm(force)
                    if mag > 5.0:
                        force = (force / mag) * 5.0
                    
                    self.nodes[ref]["pos"] += force * k
                    
                    # Boundary clamping
                    self.nodes[ref]["pos"][0] = np.clip(self.nodes[ref]["pos"][0], 5, self.width-5)
                    self.nodes[ref]["pos"][1] = np.clip(self.nodes[ref]["pos"][1], 5, self.height-5)

        log.info("[PlacerV2] Solver converged.")

    def get_solved_positions(self) -> List[Dict[str, Any]]:
        """Return results for the Orchestrator/IPC."""
        results = []
        for ref, state in self.nodes.items():
            results.append({
                "ref": ref,
                "x":   round(float(state["pos"][0]), 3),
                "y":   round(float(state["pos"][1]), 3),
                "rot": (0.0 if "SD" not in ref else 180.0) # Simple rule-based rotation
            })
        return results

    def get_layout_summary(self) -> Dict[str, Any]:
        """Metrics for the validation report."""
        return {
            "cluster_count": len(self.clusters),
            "component_count": len(self.nodes),
            "dimensions": (self.width, self.height)
        }
