import type { StateCreator } from 'zustand';

export type UiSlice = {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
};

export const createUiSlice: StateCreator<UiSlice, [], [], UiSlice> = (set) => ({
  sidebarOpen: true,
  toggleSidebar: () =>
    set((state) => ({
      sidebarOpen: !state.sidebarOpen,
    })),
});
