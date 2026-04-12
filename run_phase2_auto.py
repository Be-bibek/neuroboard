import sys
import os

# Append ai_core to path to resolve internal absolute imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_core'))

from ai_core.system.orchestrator import CompilerOrchestrator

def main():
    print("Initiating Phase 2 Semantic Target Route.")
    orch = CompilerOrchestrator()
    res = orch.run_full_pipeline()
    print("Completed. Final Report:", res)

if __name__ == "__main__":
    main()
