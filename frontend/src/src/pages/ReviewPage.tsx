import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { caseService } from '@/services/case.service';
import { Case, PipelineStatus, PipelineStatusDetail, CaseDecisionType } from '@/types/case.types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, CheckCircle2, XCircle, Clock, AlertCircle, RefreshCw, ThumbsUp, Eye, ThumbsDown } from 'lucide-react';
import { formatDateTime, formatTime } from '@/utils/formatters';

export const ReviewPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [pipelineDetails, setPipelineDetails] = useState<{ [key: string]: PipelineStatusDetail }>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);
  const [isSettingDecision, setIsSettingDecision] = useState(false);
  const [decisionComment, setDecisionComment] = useState('');

  useEffect(() => {
    fetchCaseDetails();
    return () => {
      // Cleanup polling on unmount
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [id]);

  useEffect(() => {
    // Start polling if there are processing pipelines
    if (caseData && shouldPoll(pipelineDetails)) {
      startPolling();
    } else {
      stopPolling();
    }
  }, [caseData, pipelineDetails]);

  const fetchCaseDetails = async () => {
    if (!id) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await caseService.getCaseById(id);
      
      // Call status API at least once to get enriched pipeline details
      const statusData = await caseService.getCaseStatus(id);
      setPipelineDetails(statusData.pipeline_status);
      setLastUpdated(new Date());
      
      // Merge case data with updated pipeline status
      const updatedStatus: any = {};
      Object.entries(statusData.pipeline_status).forEach(([key, detail]) => {
        updatedStatus[key] = detail.status;
      });
      
      setCaseData({ ...data, pipeline_status: updatedStatus });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load case details');
    } finally {
      setIsLoading(false);
    }
  };

  const pollStatus = async () => {
    if (!id) return;

    try {
      const statusData = await caseService.getCaseStatus(id);
      setPipelineDetails(statusData.pipeline_status);
      setLastUpdated(new Date());
      
      // Update only pipeline status without touching other fields like decision
      setCaseData(prevData => {
        if (!prevData) return prevData;
        
        const updatedStatus: any = {};
        Object.entries(statusData.pipeline_status).forEach(([key, detail]) => {
          updatedStatus[key] = detail.status;
        });
        
        return { ...prevData, pipeline_status: updatedStatus };
      });
    } catch (err: any) {
      console.error('Polling error:', err);
    }
  };

  const shouldPoll = (details: { [key: string]: PipelineStatusDetail }): boolean => {
    const statuses = Object.values(details).map(d => d.status);
    if (statuses.length === 0) return false;

    // Continue polling ONLY if any pipeline is actively processing
    return statuses.some(s => s === PipelineStatus.PROCESSING);
  };

  const startPolling = () => {
    if (pollingIntervalRef.current) return; // Already polling

    setIsPolling(true);
    
    // Start polling every 5 seconds (don't poll immediately since fetchCaseDetails already did)
    pollingIntervalRef.current = setInterval(() => {
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

  const getOverallStatus = () => {
    const statuses = Object.values(pipelineDetails).map(d => d.status);
    if (statuses.length === 0) return null;

    const allCompleted = statuses.every(
      s => s === PipelineStatus.EXTRACTED || s === PipelineStatus.REVIEWED
    );
    if (allCompleted) {
      return { type: 'success', message: 'All processing completed successfully!' };
    }

    const allFailed = statuses.every(s => s === PipelineStatus.FAILED);
    if (allFailed) {
      return { type: 'error', message: 'Processing failed for all pipelines' };
    }

    const anyProcessing = statuses.some(s => s === PipelineStatus.PROCESSING);
    if (anyProcessing) {
      return { type: 'info', message: 'Processing in progress...' };
    }

    return null;
  };

  const getPipelineIcon = (status: PipelineStatus) => {
    switch (status) {
      case PipelineStatus.EXTRACTED:
      case PipelineStatus.REVIEWED:
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case PipelineStatus.PROCESSING:
        return <Clock className="h-5 w-5 text-blue-600 animate-pulse" />;
      case PipelineStatus.FAILED:
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-400" />;
    }
  };

  const getPipelineStatusBadge = (status: PipelineStatus) => {
    switch (status) {
      case PipelineStatus.EXTRACTED:
        return <Badge variant="success">Extracted</Badge>;
      case PipelineStatus.REVIEWED:
        return <Badge variant="success">Reviewed</Badge>;
      case PipelineStatus.PROCESSING:
        return <Badge variant="default">Processing</Badge>;
      case PipelineStatus.FAILED:
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">Not Started</Badge>;
    }
  };

  const getPipelineDisplayName = (pipeline: string) => {
    const names: { [key: string]: string } = {
      mer: 'Medical Examination Report',
      pathology: 'Pathology Reports',
      risk: 'Risk Analysis',
      face_match: 'Face Matching',
      location_check: 'Location Verification',
    };
    return names[pipeline] || pipeline;
  };

  const handleSetDecision = async (decision: CaseDecisionType) => {
    if (!id) return;

    try {
      setIsSettingDecision(true);
      await caseService.setCaseDecision(id, {
        decision,
        comment: decisionComment || undefined,
      });
      
      // Refresh case data to show updated decision
      await fetchCaseDetails();
      setDecisionComment('');
    } catch (err: any) {
      console.error('Error setting decision:', err);
      setError(err.response?.data?.detail || 'Failed to set case decision');
    } finally {
      setIsSettingDecision(false);
    }
  };

  const getCaseDecisionBadge = (decision?: string) => {
    if (!decision) return null;
    
    const variants: Record<string, any> = {
      approved: { variant: 'success', icon: CheckCircle2, label: 'Approved' },
      review: { variant: 'default', icon: Eye, label: 'Needs Review' },
      declined: { variant: 'destructive', icon: XCircle, label: 'Declined' },
    };
    
    const config = variants[decision] || variants.review;
    const Icon = config.icon;
    
    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loading text="Loading results..." />
      </div>
    );
  }

  if (error || !caseData) {
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

  const overallStatus = getOverallStatus();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate(`/cases/${id}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Case
        </Button>
        {isPolling && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Auto-refreshing...</span>
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Processing Results</CardTitle>
          <CardDescription>
            {lastUpdated && (
              <span className="text-xs">
                Last updated: {formatTime(lastUpdated)}
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {overallStatus && (
            <Alert variant={overallStatus.type === 'error' ? 'destructive' : 'default'}>
              {overallStatus.type === 'success' && <CheckCircle2 className="h-4 w-4" />}
              {overallStatus.type === 'error' && <XCircle className="h-4 w-4" />}
              {overallStatus.type === 'info' && <Clock className="h-4 w-4" />}
              <AlertDescription>
                <p className="font-medium">{overallStatus.message}</p>
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            <h3 className="font-semibold text-lg">Pipeline Status</h3>
            <div className="grid gap-4">
              {Object.entries(pipelineDetails).map(([pipeline, detail]) => {
                const status = detail.status;
                
                return (
                  <Card key={pipeline}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getPipelineIcon(status)}
                          <div>
                            <h4 className="font-medium">{getPipelineDisplayName(pipeline)}</h4>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {getPipelineStatusBadge(status)}
                          {(status === PipelineStatus.EXTRACTED || status === PipelineStatus.REVIEWED) && (
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => {
                                const routes: { [key: string]: string } = {
                                  mer: `/cases/${id}/mer-results`,
                                  pathology: `/cases/${id}/pathology-results`,
                                  risk: `/cases/${id}/risk-analysis`,
                                  face_match: `/cases/${id}/face-match`,
                                  location_check: `/cases/${id}/location-check`,
                                };
                                if (routes[pipeline]) {
                                  navigate(routes[pipeline]);
                                }
                              }}
                            >
                              View Details
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Case Decision Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Case Decision</CardTitle>
              <CardDescription>Set the final underwriting decision for this case</CardDescription>
            </div>
            {caseData.decision && getCaseDecisionBadge(caseData.decision)}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {caseData.decision ? (
            <div className="space-y-3">
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2">
                    <p className="font-medium">
                      This case has been {caseData.decision === 'approved' ? 'approved' : 
                                         caseData.decision === 'review' ? 'marked for review' : 
                                         'declined'}.
                    </p>
                    {caseData.decision_at && (
                      <p className="text-sm text-muted-foreground">
                        Decision made on: {formatDateTime(caseData.decision_at)}
                      </p>
                    )}
                    {caseData.decision_comment && (
                      <p className="text-sm">
                        <span className="font-medium">Comment:</span> {caseData.decision_comment}
                      </p>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (caseData) {
                    setCaseData({
                      ...caseData,
                      decision: undefined,
                      decision_by: undefined,
                      decision_at: undefined,
                      decision_comment: undefined,
                    });
                  }
                }}
              >
                Change Decision
              </Button>
            </div>
          ) : (
            <>
              <div>
                <label className="text-sm font-medium">Comments (Optional)</label>
                <textarea
                  className="w-full mt-2 p-3 border rounded-md resize-none"
                  rows={3}
                  placeholder="Add comments about your decision..."
                  value={decisionComment}
                  onChange={(e) => setDecisionComment(e.target.value)}
                  disabled={isSettingDecision}
                />
              </div>
              
              <div className="grid grid-cols-3 gap-3">
                <Button
                  variant="default"
                  className="bg-green-600 hover:bg-green-700"
                  onClick={() => handleSetDecision('approved')}
                  disabled={isSettingDecision}
                >
                  <ThumbsUp className="h-4 w-4 mr-2" />
                  Approve
                </Button>
                <Button
                  variant="default"
                  onClick={() => handleSetDecision('review')}
                  disabled={isSettingDecision}
                >
                  <Eye className="h-4 w-4 mr-2" />
                  Needs Review
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => handleSetDecision('declined')}
                  disabled={isSettingDecision}
                >
                  <ThumbsDown className="h-4 w-4 mr-2" />
                  Decline
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <div className="flex gap-3">
        <Button onClick={() => navigate(`/cases/${id}`)}>
          Back to Case
        </Button>
        <Button variant="outline" onClick={() => navigate('/dashboard')}>
          Go to Dashboard
        </Button>
      </div>
    </div>
  );
};
