export enum CaseStatus {
  CREATED = 'created',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum DocumentType {
  MER = 'mer',
  PATHOLOGY = 'pathology',
  PHOTO = 'photo',
  ID_PROOF = 'id_proof',
}

export enum PipelineStatus {
  NOT_STARTED = 'not_started',
  PROCESSING = 'processing',
  EXTRACTED = 'extracted',
  REVIEWED = 'reviewed',
  FAILED = 'failed',
}

export interface FileEntry {
  id: string;
  file_name: string;
  content_type: string;
  url: string;
  uploaded_at: string;
}

export interface PipelineStatuses {
  mer?: PipelineStatus;
  pathology?: PipelineStatus;
  risk?: PipelineStatus;
  face_match?: PipelineStatus;
  location_check?: PipelineStatus;
  test_verification?: PipelineStatus;
}

export interface Case {
  id: string;
  case_name: string;
  pipeline_status: PipelineStatuses;
  documents: {
    [key in DocumentType]?: FileEntry[];
  };
  decision?: 'approved' | 'review' | 'declined';
  decision_by?: string;
  decision_at?: string;
  decision_comment?: string;
  created_at: string;
  updated_at: string;
}

export interface CaseListResponse {
  cases: Case[];
}

export interface ProcessingStatus {
  job_id: string;
  status: string;
}

export interface RiskSummary {
  job_id: string;
  summary: string;
}

export interface PipelineResult {
  pipeline: string;
  status: PipelineStatus;
  result: any;
}

export interface ProcessAllResponse {
  case_id: string;
  pipelines_triggered: string[];
  pipelines_skipped: string[];
  results: {
    [key: string]: PipelineResult;
  };
}

export interface PipelineStatusDetail {
  status: PipelineStatus;
  version?: number;
  fields_count?: number;
  source?: string;
  created_at?: string;
}

export interface CaseStatusResponse {
  case_id: string;
  case_name: string;
  pipeline_status: {
    [key: string]: PipelineStatusDetail;
  };
  decision?: 'approved' | 'review' | 'declined';
  decision_by?: string;
  decision_at?: string;
  updated_at: string;
}

// ─── Pathology Types ─────────────────────────────────────────────────────────

export interface PathologyField {
  id: string;
  key: string;              // parameter name (standardized or original)
  value?: string;
  unit?: string;
  reference_range?: string; // Range from report
  config_range?: string;    // Range from config (standard)
  range_status?: string;    // "normal" | "abnormal" | null
  flag?: string;            // deprecated, use range_status
  method?: string;
  reference_name?: string;  // original name from report
  sample_type?: string;     // "blood" | "urine" | "stool"
  page_number?: number;     // source page in document (1-indexed)
  section_path?: string[];
  is_standard: boolean;
  source: string;
}

export interface PathologySummaryResponse {
  case_id: string;
  version: number;
  total: number;           // Total params extracted
  normal_count: number;    // Params in normal range
  abnormal_count: number;  // Params out of range  
  no_range_count: number;  // Params with no range
}

export interface MERSummaryResponse {
  case_id: string;
  version: number;
  total_fields: number;         // Total fields extracted
  high_confidence_count: number; // Fields with >= 90% confidence
  low_confidence_count: number;  // Fields with < 90% confidence
  yes_answer_count: number;      // Y/N questions with "Yes" (flags)
}

export interface PathologyResultResponse {
  id: string;
  case_id: string;
  version: number;
  source: string;
  patient_info: any;
  lab_info: any;
  report_info: any;
  fields: PathologyField[];
  created_at: string;
}

export interface PathologyVersionEntry {
  id: string;
  version: number;
  source: string;
  created_at: string;
}

export interface PathologyVersionsResponse {
  case_id: string;
  versions: PathologyVersionEntry[];
}

export interface PathologyImportResponse {
  id: string;
  case_id: string;
  version: number;
  source: string;
  fields_count: number;
  changed_fields: number;
  message: string;
}

// ─── Risk Analysis Types ─────────────────────────────────────────────────────

export type RiskLevelType = 'Low' | 'Intermediate' | 'High';

export interface BasedOnInfo {
  mer_version?: number;
  pathology_version?: number;
  source_freshness: number;
}

export interface CriticalFlag {
  source: string;
  parameter: string;
  value: string;
  severity: string;
  message: string;
}

export interface Contradiction {
  type: string;
  field: string;
  mer_value?: string;
  pathology_value?: string;
  severity: string;
}


// Citation item with text and reference IDs (v1 format)
export interface CitedItem {
  text: string;
  refs: string[];
}

// v2 format types
export interface IntegrityConcern {
  flag: string;
  mer_ref: string;
  path_ref: string;
}

export interface ClinicalDiscovery {
  finding: string;
  severity: 'critical' | 'moderate' | 'mild';
  refs: string[];
}

// Structured summary (v2 latest)
export interface RiskSummaryStructured {
  mer: string;
  pathology: string;
  conclusion: string;
}

// Reference lookup info
export interface ReferenceInfo {
  source: 'pathology' | 'mer';
  param?: string;
  page?: number;
  section?: string;
  field?: string;
  value?: string;
  unit?: string;
}

export interface RiskResultResponse {
  id: string;
  case_id: string;
  version: number;
  based_on: BasedOnInfo;
  patient_info: any;
  critical_flags: CriticalFlag[];
  contradictions: Contradiction[];
  llm_response: {
    summary: string | RiskSummaryStructured;
    risk_level: string;

    // v1 format (old)
    red_flags?: CitedItem[];
    contradictions?: CitedItem[];

    // v2 format (new)
    risk_score?: number;
    applicant?: string;
    integrity_concerns?: IntegrityConcern[];
    clinical_discoveries?: ClinicalDiscovery[];
  };
  references: Record<string, ReferenceInfo>;
  created_at: string;
}

export interface RiskSummaryResponse {
  case_id: string;
  version: number;
  based_on: BasedOnInfo;
  summary: string | RiskSummaryStructured;
  risk_level: string;

  // v1 format (old)
  red_flags?: (string | CitedItem)[];
  contradictions?: (string | CitedItem)[];

  // v2 format (new)
  risk_score?: number;
  applicant?: string;
  integrity_concerns?: IntegrityConcern[];
  clinical_discoveries?: ClinicalDiscovery[];

  created_at: string;
}

export interface RiskVersionEntry {
  id: string;
  version: number;
  mer_version?: number;
  pathology_version?: number;
  source_freshness: number;
  risk_level?: string;  // "High" | "Intermediate" | "Low"
  created_at: string;
}

export interface RiskVersionsResponse {
  case_id: string;
  versions: RiskVersionEntry[];
}

// ─── Face Match Types ────────────────────────────────────────────────────────

export type FaceMatchDecisionType = 'match' | 'no_match' | 'unclear';
export type ReviewStatusType = 'pending' | 'approved' | 'rejected';

export interface FaceMatchResultResponse {
  id: string;
  case_id: string;
  version: number;
  match: boolean;
  match_percent: number;
  decision: FaceMatchDecisionType;
  message: string;
  photo_file_id: string;
  id_file_id: string;
  photo_url: string;
  id_url: string;
  review_status: ReviewStatusType;
  reviewed_by?: string;
  reviewed_at?: string;
  review_comment?: string;
  created_at: string;
}

export interface FaceMatchReviewRequest {
  status: 'approved' | 'rejected';
  comment?: string;
}

export interface FaceMatchReviewResponse {
  case_id: string;
  review_status: ReviewStatusType;
  reviewed_by: string;
  reviewed_at: string;
  review_comment?: string;
  message: string;
}

// ─── Case Decision Types ─────────────────────────────────────────────────────

export type CaseDecisionType = 'approved' | 'review' | 'declined';

export interface SetCaseDecisionRequest {
  decision: CaseDecisionType;
  comment?: string;
}

export interface SetCaseDecisionResponse {
  case_id: string;
  decision: CaseDecisionType;
  decision_by: string;
  decision_at: string;
  decision_comment?: string;
  message: string;
}

// ─── Test Verification Types ─────────────────────────────────────────────────

export type TestVerificationStatusType = 'complete' | 'missing_tests' | 'requirements_page_not_found' | 'extraction_failed';

export interface RequiredTest {
  category: string;
  test_name: string;
  found: boolean;
  pathology_value?: string;
}

export interface TestVerificationResultResponse {
  id: string;
  case_id: string;
  version: number;
  page_found: boolean;
  proposal_number?: string;
  life_assured_name?: string;
  ins_test_remark?: string;
  hi_test_remark?: string;
  extraction_confidence: number;
  raw_requirements: string[];
  required_tests: RequiredTest[];
  total_required: number;
  total_found: number;
  total_missing: number;
  missing_tests: string[];
  status: TestVerificationStatusType;
  mer_result_version?: number;
  pathology_result_version?: number;
  created_at: string;
}

export interface TestVerificationSummaryResponse {
  case_id: string;
  version: number;
  status: TestVerificationStatusType;
  total_required: number;
  total_found: number;
  total_missing: number;
  missing_tests: string[];
}

// ─── Dashboard Types ──────────────────────────────────────────────────────────

export interface CaseDashboardSummary {
  id: string;
  case_name: string;
  created_at: string;
  pipeline_status: Record<string, string>;
  decision?: CaseDecisionType;

  // Risk
  risk_level?: RiskLevelType;

  // Test verification
  tests_required?: number;
  tests_found?: number;

  // MER confidence
  mer_high_confidence_pct?: number;
  mer_low_confidence_count?: number;

  // Face match
  face_match_decision?: FaceMatchDecisionType;

  // Location check
  location_check_decision?: 'pass' | 'needs_review' | 'fail' | 'insufficient';

  // Computed flag
  needs_attention: boolean;
}

export interface CaseDashboardResponse {
  cases: CaseDashboardSummary[];
  total: number;
  awaiting_decision: number;
  decided: number;
  needs_attention_count: number;
  high_risk_count: number;
}

export type DashboardFilterType = 'all' | 'pending' | 'decided' | 'attention';
