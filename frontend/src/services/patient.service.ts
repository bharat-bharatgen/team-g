import api from './api';

export interface PatientInfo {
  available: boolean;
  name?: string;
  age?: number;
  gender?: string;
  dob?: string;
  proposal_number?: string;
}

export const patientService = {
  async getPatientInfo(caseId: string): Promise<PatientInfo> {
    const response = await api.get(`/cases/${caseId}/mer/patient-info`);
    return response.data;
  },
};
