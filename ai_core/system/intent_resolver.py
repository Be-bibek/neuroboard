"""
Dependency Graph for NeuroBoard IPC Engine
Defines the prerequisites logic required for higher-order modules.
"""

DEPENDENCIES = {
    "NVME_SLOT": ["PCIE_CONNECTOR", "POWER", "GPIO_HEADER"],
    "PCIE_CONNECTOR": ["GPIO_HEADER"],
    "LED": ["POWER"],
    "POWER": [],
    "GPIO_HEADER": []
}

class IntentResolver:
    """
    Parses an intent map of target modules and flattens out all dependencies 
    into an ordered execution list.
    """
    def __init__(self, graph=DEPENDENCIES):
        self.graph = graph

    def resolve(self, requested_modules):
        """
        Takes a list of module strings like ['NVME_SLOT']
        Returns a deduplicated, ordered list resolving prereqs first.
        """
        resolved = []
        visited = set()

        def dfs(node):
            if node in visited:
                return
            
            # Recurse through dependencies first
            deps = self.graph.get(node, [])
            for dep in deps:
                dfs(dep)
                
            visited.add(node)
            resolved.append(node)

        for module in requested_modules:
            dfs(module)
            
        return resolved

if __name__ == "__main__":
    resolver = IntentResolver()
    res = resolver.resolve(["NVME_SLOT"])
    print(f"Resolving 'NVME_SLOT' -> {res}")
