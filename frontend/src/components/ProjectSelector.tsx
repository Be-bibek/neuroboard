import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Folder, ChevronDown, Check } from 'lucide-react';
import { useNeuroStore } from '../store/useNeuroStore';

const API = "http://localhost:8000";

export const ProjectSelector: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([]);
  const [activeProject, setActiveProject] = useState<any>(null);
  const [isOpen, setIsOpen] = useState(false);

  const fetchProjects = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/projects`);
      setProjects(res.data.projects);
      
      const activeRes = await axios.get(`${API}/api/v1/projects/active`);
      if (activeRes.data.status === 'success') {
        setActiveProject(activeRes.data.project);
      }
    } catch (e) {
      console.error("Failed to fetch projects", e);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleSelect = async (path: string) => {
    try {
      setIsOpen(false);
      await axios.post(`${API}/api/v1/projects/load`, { path });
      // Reload active project
      fetchProjects();
      
      // Clear UI state when project changes
      window.dispatchEvent(new Event('projectChanged'));
      
      // In a real app we might want to reset the workflow graph and PCB canvas here
      useNeuroStore.setState({ syncStatus: "DISCONNECTED" });
      setTimeout(() => useNeuroStore.setState({ syncStatus: "CONNECTED" }), 500); // Simulate reconnect
      
    } catch (e) {
      console.error("Failed to load project", e);
    }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
      >
        <Folder size={14} className="text-indigo-400" />
        <span className="text-xs font-medium text-white/90">
          {activeProject ? activeProject.name : 'Select Project'}
        </span>
        <ChevronDown size={14} className="text-white/50" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 rounded-xl bg-zinc-900 border border-white/10 shadow-2xl overflow-hidden z-50">
          <div className="p-2 border-b border-white/5 bg-white/5">
            <span className="text-[10px] font-bold text-white/50 uppercase tracking-widest px-2">Workspaces</span>
          </div>
          <div className="max-h-60 overflow-y-auto p-1">
            {projects.length === 0 ? (
              <div className="px-3 py-4 text-xs text-center text-white/40">
                No KiCad projects found in workspace.
              </div>
            ) : (
              projects.map(p => (
                <button
                  key={p.path}
                  onClick={() => handleSelect(p.path)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left text-xs transition-colors
                    ${activeProject?.path === p.path ? 'bg-indigo-500/20 text-indigo-300' : 'text-white/80 hover:bg-white/5'}
                  `}
                >
                  <div className="flex flex-col overflow-hidden">
                    <span className="font-medium truncate">{p.name}</span>
                    <span className="text-[10px] text-white/40 truncate mt-0.5">{p.path}</span>
                  </div>
                  {activeProject?.path === p.path && <Check size={14} className="text-indigo-400 flex-shrink-0 ml-2" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
