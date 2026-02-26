import api from './api';
import { 
  Case, 
  CaseListResponse, 
  ProcessingStatus, 
  RiskSummary, 
  ProcessAllResponse, 
  CaseStatusResponse,
  SetCaseDecisionRequest,
  SetCaseDecisionResponse,
  CaseDashboardResponse,
  DashboardFilterType
} from '@/types/case.types';

export const caseService = {
  createCase: async (caseName: string): Promise<Case> => {
    const response = await api.post<Case>('/cases/', { case_name: caseName });
    return response.data;
  },

  getCases: async (): Promise<CaseListResponse> => {
    const response = await api.get<CaseListResponse>('/cases/');
    return response.data;
  },

  getCaseById: async (caseId: string): Promise<Case> => {
    const response = await api.get<Case>(`/cases/${caseId}`);
    return response.data;
  },

  processAll: async (caseId: string): Promise<ProcessAllResponse> => {
    const response = await api.post<ProcessAllResponse>(`/cases/${caseId}/process-all`);
    return response.data;
  },

  getCaseStatus: async (caseId: string): Promise<CaseStatusResponse> => {
    const response = await api.get<CaseStatusResponse>(`/cases/${caseId}/status`);
    return response.data;
  },

  getProcessingStatus: async (jobId: string): Promise<ProcessingStatus> => {
    const response = await api.get<ProcessingStatus>(`/processing/status/${jobId}`);
    return response.data;
  },

  getRiskSummary: async (jobId: string): Promise<RiskSummary> => {
    const response = await api.get<RiskSummary>(`/summary/${jobId}`);
    return response.data;
  },

  setCaseDecision: async (
    caseId: string, 
    decisionData: SetCaseDecisionRequest
  ): Promise<SetCaseDecisionResponse> => {
    const response = await api.patch<SetCaseDecisionResponse>(
      `/cases/${caseId}/decision`,
      decisionData
    );
    return response.data;
  },

  getDashboard: async (filter: DashboardFilterType = 'all'): Promise<CaseDashboardResponse> => {
    const response = await api.get<CaseDashboardResponse>('/cases/dashboard', {
      params: { filter },
    });
    return response.data;
  },

  deleteCase: async (caseId: string): Promise<{ case_id: string; message: string }> => {
    const response = await api.delete<{ case_id: string; message: string }>(`/cases/${caseId}`);
    return response.data;
  },
};
