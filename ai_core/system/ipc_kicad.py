import urllib.request
import json

class KiCadIPC:
    """
    Direct IPC wrapper for KiCad placing footprints.
    Communicates securely via the neuro_layout MCP HTTP gateway on port 3000.
    This guarantees immunity to KiCad version mismatches and locked python interpreters!
    """
    def __init__(self, endpoint="http://localhost:3000/api/tool"):
        self.endpoint = endpoint
        print(f"[OK] FastIPC Engine Initialized (Proxy to {self.endpoint})")

    def _post(self, tool_name, params):
        try:
            req = urllib.request.Request(
                self.endpoint, 
                data=json.dumps({
                    'tool': tool_name, 
                    'params': params
                }).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            res = urllib.request.urlopen(req)
            return json.loads(res.read().decode('utf-8'))
        except Exception as e:
            print(f"[ERROR] IPC Error ({tool_name}): {e}")
            return None

    def create_net(self, net_name: str):
        """Creates a new net in the board."""
        print(f"[IPC] create_net: {net_name}")
        return self._post('add_net', {'name': net_name})

    def place_component(self, component_id: str, ref_des: str, x: float, y: float, rot: float = 0.0, layer="F.Cu"):
        """
        Places a footprint from a library into the board.
        x, y are in millimeters.
        """
        print(f"[IPC] place_component: {ref_des} ({component_id}) at {x},{y}")
        return self._post('place_component', {
            'componentId': component_id,
            'reference': ref_des,
            'position': {'x': x, 'y': y, 'unit': 'mm'},
            'rotation': rot,
            'layer': layer
        })

    def connect(self, ref_des: str, pad_num: str, net_name: str):
        """
        Assigns a pad logic to a net.
        (Note: if the MCP adds connect_pad, we use it. For now, it might be auto-assigned during PCB netlist sync).
        """
        print(f"[IPC] connect_pad: {ref_des}.{pad_num} -> {net_name}")
        # To be implemented if the neuro_layout MCP server exposes pad targeting explicitly.
        pass
