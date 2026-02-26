import api from './api';
import { RiskResultResponse, RiskSummaryResponse, RiskVersionsResponse } from '@/types/case.types';

export const riskService = {
  getResult: async (caseId: string, version?: number): Promise<RiskResultResponse> => {
    const params = version ? `?version=${version}` : '';
    const response = await api.get<RiskResultResponse>(`/cases/${caseId}/risk/result${params}`);
    return response.data;
  },

  getSummary: async (caseId: string, version?: number): Promise<RiskSummaryResponse> => {
    const params = version ? `?version=${version}` : '';
    const response = await api.get<RiskSummaryResponse>(`/cases/${caseId}/risk/summary${params}`);
    return response.data;
  },

  getVersions: async (caseId: string): Promise<RiskVersionsResponse> => {
    const response = await api.get<RiskVersionsResponse>(`/cases/${caseId}/risk/versions`);
    return response.data;
  },
};
