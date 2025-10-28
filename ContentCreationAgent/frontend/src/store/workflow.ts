import { create } from 'zustand';
import type { WorkflowState, WorkflowUpdate } from '../types';

interface WorkflowStore {
  currentWorkflow: WorkflowState | null;
  workflows: WorkflowState[];
  realtimeUpdates: WorkflowUpdate[];
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;

  setCurrentWorkflow: (workflow: WorkflowState | null) => void;
  addWorkflow: (workflow: WorkflowState) => void;
  updateWorkflow: (update: Partial<WorkflowState>) => void;
  updateWorkflowById: (
    workflowId: string,
    update: Partial<WorkflowState>
  ) => void;
  setWorkflows: (workflows: WorkflowState[]) => void;
  addRealtimeUpdate: (update: WorkflowUpdate) => void;
  setIsLoading: (loading: boolean) => void;
  setIsCreating: (creating: boolean) => void;
  setError: (error: string | null) => void;
}

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  currentWorkflow: null,
  workflows: [],
  realtimeUpdates: [],
  isLoading: false,
  isCreating: false,
  error: null,

  setCurrentWorkflow: (workflow) => set({ currentWorkflow: workflow }),

  addWorkflow: (workflow) =>
    set((state) => ({
      workflows: [workflow, ...state.workflows].slice(0, 50),
    })),

  updateWorkflow: (update) =>
    set((state) => ({
      currentWorkflow: state.currentWorkflow
        ? { ...state.currentWorkflow, ...update }
        : null,
      workflows: state.workflows.map((w) =>
        w.workflow_id === state.currentWorkflow?.workflow_id
          ? { ...w, ...update }
          : w
      ),
    })),

  updateWorkflowById: (workflowId, update) =>
    set((state) => ({
      workflows: state.workflows.map((w) =>
        w.workflow_id === workflowId ? { ...w, ...update } : w
      ),
    })),

  setWorkflows: (workflows) => set({ workflows }),

  addRealtimeUpdate: (update) =>
    set((state) => ({
      realtimeUpdates: [update, ...state.realtimeUpdates].slice(0, 100),
    })),

  setIsLoading: (loading) => set({ isLoading: loading }),
  setIsCreating: (creating) => set({ isCreating: creating }),
  setError: (error) => set({ error }),
}));
