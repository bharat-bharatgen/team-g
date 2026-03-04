import { create } from 'zustand';
import { Case } from '@/types/case.types';

interface CaseState {
  cases: Case[];
  currentCase: Case | null;
  isLoading: boolean;
  error: string | null;
  setCases: (cases: Case[]) => void;
  setCurrentCase: (currentCase: Case | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  addCase: (newCase: Case) => void;
  updateCase: (updatedCase: Case) => void;
  removeCase: (caseId: string) => void;
}

export const useCaseStore = create<CaseState>((set) => ({
  cases: [],
  currentCase: null,
  isLoading: false,
  error: null,

  setCases: (cases) => set({ cases }),
  setCurrentCase: (currentCase) => set({ currentCase }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),

  addCase: (newCase) =>
    set((state) => ({
      cases: [newCase, ...state.cases],
    })),

  updateCase: (updatedCase) =>
    set((state) => ({
      cases: state.cases.map((c) => (c.id === updatedCase.id ? updatedCase : c)),
      currentCase:
        state.currentCase?.id === updatedCase.id ? updatedCase : state.currentCase,
    })),

  removeCase: (caseId) =>
    set((state) => ({
      cases: state.cases.filter((c) => c.id !== caseId),
      currentCase: state.currentCase?.id === caseId ? null : state.currentCase,
    })),
}));
