import { PipelineStatuses, PipelineStatus, CaseStatus } from '@/types/case.types';

/**
 * Derive an overall case status from pipeline statuses
 */
export const deriveOverallStatus = (pipelineStatus: PipelineStatuses | null | undefined): CaseStatus => {
  // Handle null or undefined pipeline status
  if (!pipelineStatus) {
    return CaseStatus.CREATED;
  }
  
  const statuses = Object.values(pipelineStatus).filter(Boolean) as PipelineStatus[];
  
  if (statuses.length === 0) {
    return CaseStatus.CREATED;
  }

  // If any pipeline is processing, overall status is processing
  if (statuses.some(s => s === PipelineStatus.PROCESSING)) {
    return CaseStatus.PROCESSING;
  }

  // If all pipelines are failed, overall status is failed
  if (statuses.every(s => s === PipelineStatus.FAILED)) {
    return CaseStatus.FAILED;
  }

  // If any pipeline is extracted or reviewed, overall status is completed
  if (statuses.some(s => s === PipelineStatus.EXTRACTED || s === PipelineStatus.REVIEWED)) {
    return CaseStatus.COMPLETED;
  }

  // Default to created if all are not_started
  return CaseStatus.CREATED;
};
