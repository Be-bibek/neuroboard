import { create } from 'zustand';

interface UIState {
  viewMode: 'SIDEBAR' | 'PLANNING_BOARD';
  setViewMode: (mode: 'SIDEBAR' | 'PLANNING_BOARD') => void;
  toggleViewMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  viewMode: 'SIDEBAR',
  setViewMode: (mode) => set({ viewMode: mode }),
  toggleViewMode: () => set((state) => ({ 
    viewMode: state.viewMode === 'SIDEBAR' ? 'PLANNING_BOARD' : 'SIDEBAR' 
  })),
}));
