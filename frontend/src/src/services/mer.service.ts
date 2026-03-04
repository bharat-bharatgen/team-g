import api from './api';
import { MERSummaryResponse } from '@/types/case.types';

export const merService = {
  getSummary: async (caseId: string, version?: number): Promise<MERSummaryResponse> => {
    const params = version ? `?version=${version}` : '';
    const response = await api.get<MERSummaryResponse>(`/cases/${caseId}/mer/summary${params}`);
    return response.data;
  },
};
