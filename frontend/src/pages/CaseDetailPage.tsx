import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { caseService } from '@/services/case.service';
import { documentService } from '@/services/document.service';
import { patientService, PatientInfo } from '@/services/patient.service';
import { useCaseStore } from '@/store/caseStore';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { CaseSummaryTab } from '@/components/cases/CaseSummaryTab';
import { CaseDetailsTab } from '@/components/cases/CaseDetailsTab';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Calendar, AlertCircle, LayoutDashboard, FileStack, RefreshCw, User, Loader2 } from 'lucide-react';
import { formatDateTime } from '@/utils/formatters';
import { deriveOverallStatus } from '@/utils/caseHelpers';
import { PipelineStatus, PipelineStatusDetail, CaseDecisionType } from '@/types/case.types';

export const CaseDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { currentCase, setCurrentCase } = useCaseStore();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Initialize tab from URL param or default to 'summary'
  const initialTab = searchParams.get('tab') === 'documents' ? 'details' : 'summary';
  const [activeTab, setActiveTab] = useState(initialTab);
  
  const [pipelineDetails, setPipelineDetails] = useState<{ [key: string]: PipelineStatusDetail }>({});
  const [isPolling, setIsPolling] = useState(false);
  const [isSettingDecision, setIsSettingDecision] = useState(false);
  const [patientInfo, setPatientInfo] = useState<PatientInfo | null>(null);
  const [isLoadingPatient, setIsLoadingPatient] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);
  /** After Process All, we poll until these pipelines are all terminal (extracted/reviewed/failed). */
  const triggeredPipelinesRef = useRef<string[]>([]);

  const TERMINAL_STATUSES = [PipelineStatus.EXTRACTED, PipelineStatus.REVIEWED, PipelineStatus.FAILED];

  const allTriggeredTerminal = (
    details: { [key: string]: PipelineStatusDetail },
    triggered: string[]
  ): boolean => {
    if (triggered.length === 0) return true;
    return triggered.every(
      (p) => details[p] && TERMINAL_STATUSES.includes(details[p].status as PipelineStatus)
    );
  };

  const fetchCaseDetails = async (showLoading = true) => {
    if (!id) return;

    if (showLoading) {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [caseData, documentsData] = await Promise.all([
        caseService.getCaseById(id),
        documentService.getDocuments(id),
      ]);

      // Try to get pipeline status
      try {
        const statusData = await caseService.getCaseStatus(id);
        setPipelineDetails(statusData.pipeline_status);
        
        // Merge pipeline status
        const updatedStatus: any = {};
        Object.entries(statusData.pipeline_status).forEach(([key, detail]) => {
          updatedStatus[key] = detail.status;
        });
        
        setCurrentCase({
          ...caseData,
          documents: documentsData.documents,
          pipeline_status: updatedStatus,
        });
      } catch {
        // No pipeline status yet
        setCurrentCase({
          ...caseData,
          documents: documentsData.documents,
        });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load case details');
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  };

  // Light refresh - only updates documents without showing loading spinner
  const refreshDocuments = async () => {
    if (!id || !currentCase) return;

    try {
      const documentsData = await documentService.getDocuments(id);
      setCurrentCase({
        ...currentCase,
        documents: documentsData.documents,
      });
    } catch (err: any) {
      console.error('Error refreshing documents:', err);
    }
  };

  // Fetch patient info from MER results
  const fetchPatientInfo = async () => {
    if (!id) return;

    setIsLoadingPatient(true);
    try {
      const info = await patientService.getPatientInfo(id);
      setPatientInfo(info);
    } catch (err: any) {
      console.error('Error fetching patient info:', err);
      setPatientInfo({ available: false });
    } finally {
      setIsLoadingPatient(false);
    }
  };

  const pollStatus = async () => {
    if (!id) return;

    try {
      const statusData = await caseService.getCaseStatus(id);
      setPipelineDetails(statusData.pipeline_status);

      // Update pipeline status in case data (use direct pattern, not callback)
      if (currentCase) {
        const updatedStatus: any = {};
        Object.entries(statusData.pipeline_status).forEach(([key, detail]: [string, any]) => {
          updatedStatus[key] = detail.status;
        });

        setCurrentCase({ ...currentCase, pipeline_status: updatedStatus });
      }

      // Stop polling when all pipelines we triggered are terminal
      const triggered = triggeredPipelinesRef.current;
      if (triggered.length > 0 && allTriggeredTerminal(statusData.pipeline_status, triggered)) {
        triggeredPipelinesRef.current = [];
        stopPolling();
      }
    } catch (err: any) {
      console.error('Polling error:', err);
    }
  };

  const shouldPoll = (): boolean => {
    const statuses = Object.values(pipelineDetails).map((d) => d.status);
    if (statuses.length === 0) return false;
    return statuses.some((s) => s === PipelineStatus.PROCESSING);
  };

  const startPolling = () => {
    if (pollingIntervalRef.current) return;

    setIsPolling(true);
    pollingIntervalRef.current = window.setInterval(() => {
      pollStatus();
    }, 5000);
  };

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  };

  useEffect(() => {
    fetchCaseDetails();
    fetchPatientInfo();
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [id]);

  useEffect(() => {
    if (shouldPoll()) {
      startPolling();
    } else if (triggeredPipelinesRef.current.length === 0) {
      stopPolling();
    }
    // When triggeredPipelinesRef is non-empty, pollStatus() will stop polling once all are terminal
  }, [pipelineDetails]);

  // Re-fetch patient info when MER status changes to extracted or reviewed
  useEffect(() => {
    const merStatus = pipelineDetails.mer?.status;
    if (merStatus === 'extracted' || merStatus === 'reviewed') {
      if (!patientInfo?.available) {
        fetchPatientInfo();
      }
    }
  }, [pipelineDetails.mer?.status]);

  const handleProcessAll = async () => {
    if (!id) return;

    setIsProcessing(true);
    setError(null);

    try {
      const result = await caseService.processAll(id);
      triggeredPipelinesRef.current = result.pipelines_triggered ?? [];
      setActiveTab('summary');
      await pollStatus();
      if (triggeredPipelinesRef.current.length > 0) {
        startPolling();
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to start processing';
      setError(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSetDecision = async (decision: CaseDecisionType, comment?: string) => {
    if (!id) return;

    try {
      setIsSettingDecision(true);
      await caseService.setCaseDecision(id, {
        decision,
        comment,
      });
      await fetchCaseDetails();
    } catch (err: any) {
      console.error('Error setting decision:', err);
      setError(err.response?.data?.detail || 'Failed to set case decision');
    } finally {
      setIsSettingDecision(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loading text="Loading case details..." />
      </div>
    );
  }

  if (error && !currentCase) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || 'Case not found'}</AlertDescription>
        </Alert>
        <Button variant="outline" onClick={() => navigate('/dashboard')} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
      </div>
    );
  }

  if (!currentCase) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Button>
        {isPolling && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Auto-refreshing...</span>
          </div>
        )}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Case Header Card */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-2xl">{currentCase.case_name}</CardTitle>
              <div className="flex items-center gap-3 mt-2">
                <StatusBadge status={deriveOverallStatus(currentCase.pipeline_status)} />
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>{formatDateTime(currentCase.created_at)}</span>
                </div>
              </div>
              
              {/* Patient Info Section */}
              <div className="mt-4 pt-4 border-t border-slate-100">
                {isLoadingPatient ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Finding client details...</span>
                  </div>
                ) : patientInfo?.available && patientInfo.name ? (
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
                      <div>
                        <span className="text-muted-foreground">Client: </span>
                        <span className="font-medium">{patientInfo.name}</span>
                      </div>
                      {patientInfo.age && (
                        <div>
                          <span className="text-muted-foreground">Age: </span>
                          <span className="font-medium">{patientInfo.age} years</span>
                        </div>
                      )}
                      {patientInfo.gender && (
                        <div>
                          <span className="text-muted-foreground">Gender: </span>
                          <span className="font-medium">{patientInfo.gender}</span>
                        </div>
                      )}
                      {patientInfo.dob && (
                        <div>
                          <span className="text-muted-foreground">DOB: </span>
                          <span className="font-medium">{patientInfo.dob}</span>
                        </div>
                      )}
                      {patientInfo.proposal_number && (
                        <div>
                          <span className="text-muted-foreground">Proposal #: </span>
                          <span className="font-medium">{patientInfo.proposal_number}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <User className="h-4 w-4" />
                    <span>Client details will appear after MER processing</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="summary" className="gap-2">
            <LayoutDashboard className="h-4 w-4" />
            Summary
          </TabsTrigger>
          <TabsTrigger value="details" className="gap-2">
            <FileStack className="h-4 w-4" />
            Documents
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <CaseSummaryTab
            caseData={currentCase}
            pipelineDetails={pipelineDetails}
            onSetDecision={handleSetDecision}
            isSettingDecision={isSettingDecision}
            isProcessingStarted={isProcessing}
          />
        </TabsContent>

        <TabsContent value="details">
          <CaseDetailsTab
            caseData={currentCase}
            pipelineDetails={pipelineDetails}
            onUpdate={refreshDocuments}
            onProcessAll={handleProcessAll}
            isProcessing={isProcessing}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};
