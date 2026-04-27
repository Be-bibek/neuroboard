import os
from pathlib import Path
from typing import List, Dict, Optional

class ProjectManager:
    def __init__(self, workspace_dir: str = None):
        if not workspace_dir:
            # Default to a "projects" folder in the NeuroBoard root
            self.workspace_dir = Path(__file__).resolve().parent.parent.parent / "projects"
        else:
            self.workspace_dir = Path(workspace_dir)
            
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.active_project: Optional[Dict[str, str]] = None
        
    def list_projects(self) -> List[Dict[str, str]]:
        projects = []
        # Find all .kicad_pro files
        for pro_file in self.workspace_dir.rglob("*.kicad_pro"):
            pcb_file = pro_file.with_suffix(".kicad_pcb")
            projects.append({
                "name": pro_file.stem,
                "path": str(pro_file.parent),
                "pro_file": str(pro_file),
                "pcb_file": str(pcb_file) if pcb_file.exists() else None
            })
        return projects
        
    def load_project(self, project_path: str) -> bool:
        path = Path(project_path)
        if not path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
            
        pro_files = list(path.glob("*.kicad_pro"))
        if not pro_files:
            raise ValueError(f"No .kicad_pro file found in {project_path}")
            
        pcb_file = pro_files[0].with_suffix(".kicad_pcb")
        
        self.active_project = {
            "name": pro_files[0].stem,
            "path": str(path),
            "pro_file": str(pro_files[0]),
            "pcb_file": str(pcb_file) if pcb_file.exists() else None
        }
        return True
        
    def get_active_project(self) -> Optional[Dict[str, str]]:
        return self.active_project
        
    def close_project(self):
        self.active_project = None

# Global singleton
project_manager = ProjectManager()
