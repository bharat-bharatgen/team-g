import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Case, PipelineStatus, PipelineStatusDetail, CaseDecisionType, RiskSummaryResponse, FaceMatchResultResponse, PathologySummaryResponse, TestVerificationResultResponse, MERSummaryResponse } from '@/types/case.types';
import { LocationCheckResult, locationCheckService } from '@/services/location-check.service';
import { riskService } from '@/services/risk.service';
import { faceMatchService } from '@/services/face-match.service';
import { pathologyService } from '@/services/pathology.service';
import { testVerificationService } from '@/services/test-verification.service';
import { merService } from '@/services/mer.service';
import { formatDateTime } from '@/utils/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Shield,
  User,
  MapPin,
  ThumbsUp,
  ThumbsDown,
  Eye,
  AlertTriangle,
  ArrowRight,
  AlertCircle,
  FlaskConical,
  Loader2,
  ClipboardCheck,
} from 'lucide-react';

interface CaseSummaryTabProps {
  caseData: Case;
  pipelineDetails: { [key: string]: PipelineStatusDetail };
  onSetDecision: (decision: CaseDecisionType, comment?: string) => Promise<void>;
  isSettingDecision: boolean;
  isProcessingStarted?: boolean; // New prop - show processing immediately after clicking Process All
}

// Pipeline configuration
const PIPELINE_CONFIG: Record<string, { label: string; description: string; icon: any }> = {
  mer: { label: 'Medical Examination Report', description: 'Extracted patient data', icon: FileText },
  pathology: { label: 'Pathology Reports', description: 'Lab test results', icon: FlaskConical },
  risk: { label: 'Risk Assessment', description: 'Underwriting risk analysis', icon: Shield },
  face_match: { label: 'Face Verification', description: 'Photo vs ID match', icon: User },
  location_check: { label: 'Location Check', description: 'Address verification', icon: MapPin },
  test_verification: { label: 'Test Requirements', description: 'Required tests verification', icon: ClipboardCheck },
};

// Pipeline routes
const PIPELINE_ROUTES: Record<string, string> = {
  mer: 'mer-results',
  pathology: 'pathology-results',
  risk: 'risk-analysis',
  face_match: 'face-match',
  location_check: 'location-check',
  test_verification: 'test-verification',
};

export const CaseSummaryTab = ({
  caseData,
  pipelineDetails,
  onSetDecision,
  isSettingDecision,
  isProcessingStarted = false,
}: CaseSummaryTabProps) => {
  const navigate = useNavigate();
  
  // Insight data states
  const [riskData, setRiskData] = useState<RiskSummaryResponse | null>(null);
  const [faceMatchData, setFaceMatchData] = useState<FaceMatchResultResponse | null>(null);
  const [locationData, setLocationData] = useState<LocationCheckResult | null>(null);
  const [pathologyData, setPathologyData] = useState<PathologySummaryResponse | null>(null);
  const [testVerificationData, setTestVerificationData] = useState<TestVerificationResultResponse | null>(null);
  const [merData, setMerData] = useState<MERSummaryResponse | null>(null);
  const [decisionComment, setDecisionComment] = useState('');

  // Fetch insights when pipelines complete
  useEffect(() => {
    // Guard against undefined caseData.id
    if (!caseData?.id) {
      return;
    }

    const fetchInsights = async () => {
      const promises: Promise<void>[] = [];
      
      // Fetch risk data if available
      if (pipelineDetails.risk?.status === PipelineStatus.EXTRACTED || 
          pipelineDetails.risk?.status === PipelineStatus.REVIEWED) {
        promises.push(
          riskService.getSummary(caseData.id)
            .then(data => setRiskData(data))
            .catch(() => setRiskData(null))
        );
      }
      
      // Fetch face match data if available
      if (pipelineDetails.face_match?.status === PipelineStatus.EXTRACTED || 
          pipelineDetails.face_match?.status === PipelineStatus.REVIEWED) {
        promises.push(
          faceMatchService.getResult(caseData.id)
            .then(data => setFaceMatchData(data))
            .catch(() => setFaceMatchData(null))
        );
      }
      
      // Fetch location check data if available
      if (pipelineDetails.location_check?.status === PipelineStatus.EXTRACTED || 
          pipelineDetails.location_check?.status === PipelineStatus.REVIEWED) {
        promises.push(
          locationCheckService.getResult(caseData.id)
            .then(data => setLocationData(data))
            .catch(() => setLocationData(null))
        );
      }

      // Fetch pathology summary if available
      if (pipelineDetails.pathology?.status === PipelineStatus.EXTRACTED || 
          pipelineDetails.pathology?.status === PipelineStatus.REVIEWED) {
        promises.push(
          pathologyService.getSummary(caseData.id)
            .then(data => setPathologyData(data))
            .catch(() => setPathologyData(null))
        );
      }

      // Fetch MER summary if available
      if (pipelineDetails.mer?.status === PipelineStatus.EXTRACTED || 
          pipelineDetails.mer?.status === PipelineStatus.REVIEWED) {
        promises.push(
          merService.getSummary(caseData.id)
            .then(data => setMerData(data))
            .catch(() => setMerData(null))
        );
      }

      // Fetch test verification data if available
      if (pipelineDetails.test_verification?.status === PipelineStatus.EXTRACTED || 
          pipelineDetails.test_verification?.status === PipelineStatus.REVIEWED) {
        promises.push(
          testVerificationService.getResult(caseData.id)
            .then(data => setTestVerificationData(data))
            .catch(() => setTestVerificationData(null))
        );
      }
      
      await Promise.all(promises);
    };
    
    fetchInsights();
  }, [caseData?.id, pipelineDetails]);

  // Calculate stats
  const pipelineKeys = Object.keys(pipelineDetails);

  // Status helpers
  const getStatusConfig = (status?: PipelineStatus) => {
    switch (status) {
      case PipelineStatus.EXTRACTED:
      case PipelineStatus.REVIEWED:
        return { color: 'text-teal-700', bg: 'bg-teal-50', icon: CheckCircle2, label: 'Ready' };
      case PipelineStatus.PROCESSING:
        return { color: 'text-primary', bg: 'bg-primary/10', icon: Loader2, label: 'Processing', animate: true };
      case PipelineStatus.FAILED:
        return { color: 'text-red-700', bg: 'bg-red-50', icon: XCircle, label: 'Failed' };
      default:
        return { color: 'text-slate-500', bg: 'bg-slate-100', icon: Clock, label: 'Pending' };
    }
  };

  const isComplete = (status?: PipelineStatus) => 
    status === PipelineStatus.EXTRACTED || status === PipelineStatus.REVIEWED;

  // Bold, prominent color configs for risk levels
  const getRiskLevelConfig = (level: string) => {
    const configs: Record<string, { text: string; badge: string; icon: string }> = {
      High: { text: 'text-red-700', badge: 'bg-red-100 text-red-800 border-2 border-red-400', icon: 'text-red-600' },
      Intermediate: { text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800 border-2 border-amber-400', icon: 'text-amber-600' },
      Low: { text: 'text-teal-700', badge: 'bg-teal-100 text-teal-800 border-2 border-teal-400', icon: 'text-teal-600' },
    };
    return configs[level] || configs.Intermediate;
  };

  const getMatchConfig = (isMatch: boolean) => {
    if (isMatch) return { text: 'text-teal-700', bar: 'bg-teal-500' };
    return { text: 'text-red-700', bar: 'bg-red-500' };
  };

  const getLocationConfig = (decision: string) => {
    const configs: Record<string, { text: string; icon: any }> = {
      pass: { text: 'text-teal-700', icon: CheckCircle2 },
      fail: { text: 'text-red-700', icon: XCircle },
      insufficient: { text: 'text-slate-600', icon: AlertCircle },
    };
    return configs[decision] || configs.insufficient;
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
      <Badge variant={config.variant} className="gap-1 text-sm px-3 py-1">
        <Icon className="h-4 w-4" />
        {config.label}
      </Badge>
    );
  };

  const handleSetDecision = (decision: CaseDecisionType) => {
    onSetDecision(decision, decisionComment || undefined);
  };

  const handleCardClick = (pipelineKey: string) => {
    const route = PIPELINE_ROUTES[pipelineKey];
    if (route && caseData?.id) {
      navigate(`/cases/${caseData.id}/${route}`);
    }
  };

  // Render pipeline card based on status and type
  const renderPipelineCard = (key: string, detail: PipelineStatusDetail) => {
    const config = PIPELINE_CONFIG[key];
    if (!config) return null;

    const statusConfig = getStatusConfig(detail.status);
    const Icon = config.icon;
    const StatusIcon = statusConfig.icon;
    const isReady = isComplete(detail.status);
    const canClick = isReady && PIPELINE_ROUTES[key];

    // Special rendering for completed Risk Assessment
    if (key === 'risk' && isReady && riskData) {
      const isV2 = !!(riskData.integrity_concerns || riskData.clinical_discoveries);
      const integrityCount = riskData.integrity_concerns?.length ?? 0;
      const discoveryCount = riskData.clinical_discoveries?.length ?? 0;
      const redFlagCount = riskData.red_flags?.length ?? 0;
      const contradictionCount = riskData.contradictions?.length ?? 0;

      return (
        <Card 
          key={key}
          className="cursor-pointer transition-all hover:shadow-soft border-slate-200"
          onClick={() => handleCardClick(key)}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-slate-100">
                  <Shield className={`h-6 w-6 ${getRiskLevelConfig(riskData.risk_level).icon}`} />
                </div>
                <div>
                  <CardTitle className="text-lg">{config.label}</CardTitle>
                  <p className="text-sm text-muted-foreground">{config.description}</p>
                </div>
              </div>
              <Badge className={`text-lg px-4 py-2 font-bold ${getRiskLevelConfig(riskData.risk_level).badge}`}>
                {riskData.risk_level} Risk
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-3">
              <p className="text-base leading-relaxed text-foreground font-semibold line-clamp-2">
                {typeof riskData.summary === 'object' && riskData.summary !== null
                  ? riskData.summary.conclusion
                  : riskData.summary || 'Risk analysis completed.'}
              </p>
              
              <div className="flex items-center gap-4 pt-2">
                {isV2 ? (
                  <>
                    {integrityCount > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                        <span className="font-medium">{integrityCount} Integrity Issue{integrityCount !== 1 ? 's' : ''}</span>
                      </div>
                    )}
                    {discoveryCount > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <AlertCircle className="h-4 w-4 text-amber-500" />
                        <span className="font-medium">{discoveryCount} Clinical Finding{discoveryCount !== 1 ? 's' : ''}</span>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    {redFlagCount > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                        <span className="font-medium">{redFlagCount} Red Flag{redFlagCount !== 1 ? 's' : ''}</span>
                      </div>
                    )}
                    {contradictionCount > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <AlertCircle className="h-4 w-4 text-amber-500" />
                        <span className="font-medium">{contradictionCount} Contradiction{contradictionCount !== 1 ? 's' : ''}</span>
                      </div>
                    )}
                  </>
                )}
                <div className="ml-auto flex items-center gap-1 text-sm text-muted-foreground">
                  View Details <ArrowRight className="h-4 w-4" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Special rendering for completed Face Match
    if (key === 'face_match' && isReady && faceMatchData) {
      return (
        <Card 
          key={key}
          className="cursor-pointer transition-all hover:shadow-soft border-slate-200"
          onClick={() => handleCardClick(key)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100">
                <User className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className={`text-3xl font-bold ${getMatchConfig(faceMatchData.match || faceMatchData.decision === 'match').text}`}>
                  {faceMatchData.match_percent}%
                </span>
                <span className="text-sm text-muted-foreground mb-1">match</span>
              </div>
              
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all ${getMatchConfig(faceMatchData.match || faceMatchData.decision === 'match').bar}`}
                  style={{ width: `${faceMatchData.match_percent}%` }}
                />
              </div>
              
              <div className="flex items-center justify-between pt-1">
                <div className="flex gap-2">
                  <span className={`text-xs font-medium ${faceMatchData.match ? 'text-teal-700' : 'text-red-700'}`}>
                    {faceMatchData.decision === 'match' ? 'Match' : 
                     faceMatchData.decision === 'no_match' ? 'No Match' : 'Unclear'}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    · {faceMatchData.review_status === 'approved' ? 'Approved' :
                     faceMatchData.review_status === 'rejected' ? 'Rejected' : 'Pending'}
                  </span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Special rendering for completed MER
    if (key === 'mer' && isReady && merData) {
      return (
        <Card 
          key={key}
          className="cursor-pointer transition-all hover:shadow-soft border-slate-200"
          onClick={() => handleCardClick(key)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <span className="text-2xl font-bold text-foreground">{merData.total_fields}</span>
                  <p className="text-xs text-muted-foreground">Total</p>
                </div>
                <div className="h-8 w-px bg-slate-200" />
                <div className="text-center">
                  <span className="text-2xl font-bold text-teal-600">{merData.high_confidence_count}</span>
                  <p className="text-xs text-muted-foreground">≥90%</p>
                </div>
                {merData.low_confidence_count > 0 && (
                  <>
                    <div className="h-8 w-px bg-slate-200" />
                    <div className="text-center">
                      <span className="text-2xl font-bold text-amber-600">{merData.low_confidence_count}</span>
                      <p className="text-xs text-muted-foreground">&lt;90%</p>
                    </div>
                  </>
                )}
                {merData.yes_answer_count > 0 && (
                  <>
                    <div className="h-8 w-px bg-slate-200" />
                    <div className="text-center">
                      <span className="text-2xl font-bold text-red-600">{merData.yes_answer_count}</span>
                      <p className="text-xs text-muted-foreground">Flags</p>
                    </div>
                  </>
                )}
              </div>
              
              <div className="flex items-center justify-between pt-1">
                {merData.yes_answer_count > 0 ? (
                  <div className="flex items-center gap-2 text-sm text-red-600">
                    <AlertTriangle className="h-4 w-4" />
                    <span>{merData.yes_answer_count} non-ideal answer{merData.yes_answer_count !== 1 ? 's' : ''}</span>
                  </div>
                ) : (
                  <span className="text-sm text-teal-600 flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4" />
                    No conditions flagged
                  </span>
                )}
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Special rendering for completed Pathology
    if (key === 'pathology' && isReady && pathologyData) {
      return (
        <Card 
          key={key}
          className="cursor-pointer transition-all hover:shadow-soft border-slate-200"
          onClick={() => handleCardClick(key)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100">
                <FlaskConical className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <span className="text-2xl font-bold text-foreground">{pathologyData.total}</span>
                  <p className="text-xs text-muted-foreground">Total</p>
                </div>
                <div className="h-8 w-px bg-slate-200" />
                <div className="text-center">
                  <span className="text-2xl font-bold text-teal-600">{pathologyData.normal_count}</span>
                  <p className="text-xs text-muted-foreground">Normal</p>
                </div>
                {pathologyData.abnormal_count > 0 && (
                  <>
                    <div className="h-8 w-px bg-slate-200" />
                    <div className="text-center">
                      <span className="text-2xl font-bold text-red-600">{pathologyData.abnormal_count}</span>
                      <p className="text-xs text-muted-foreground">Abnormal</p>
                    </div>
                  </>
                )}
                {pathologyData.no_range_count > 0 && (
                  <>
                    <div className="h-8 w-px bg-slate-200" />
                    <div className="text-center">
                      <span className="text-2xl font-bold text-slate-500">{pathologyData.no_range_count}</span>
                      <p className="text-xs text-muted-foreground">No Range</p>
                    </div>
                  </>
                )}
              </div>
              
              <div className="flex items-center justify-between pt-1">
                {pathologyData.abnormal_count > 0 ? (
                  <div className="flex items-center gap-2 text-sm text-red-600">
                    <AlertTriangle className="h-4 w-4" />
                    <span>{pathologyData.abnormal_count} parameter{pathologyData.abnormal_count !== 1 ? 's' : ''} out of range</span>
                  </div>
                ) : (
                  <span className="text-sm text-teal-600 flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4" />
                    All values in range
                  </span>
                )}
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Special rendering for completed Location Check
    if (key === 'location_check' && isReady && locationData) {
      return (
        <Card 
          key={key} 
          className="cursor-pointer transition-all hover:shadow-soft border-slate-200"
          onClick={() => handleCardClick(key)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-base">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                {(() => {
                  const locConfig = getLocationConfig(locationData.decision);
                  const LocIcon = locConfig.icon;
                  return (
                    <>
                      <LocIcon className={`h-7 w-7 ${locConfig.text}`} />
                      <span className={`text-xl font-bold ${locConfig.text} capitalize`}>
                        {locationData.decision}
                      </span>
                    </>
                  );
                })()}
              </div>
              
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Sources Verified</p>
                <div className="flex flex-wrap gap-1">
                  {locationData.sources_detected.map((source) => (
                    <span key={source} className="inline-flex items-center gap-1 text-xs text-teal-700 capitalize">
                      <CheckCircle2 className="h-3 w-3" />
                      {source}
                    </span>
                  ))}
                  {locationData.sources_not_detected.map((source) => (
                    <span key={source} className="inline-flex items-center gap-1 text-xs text-slate-400 capitalize">
                      <XCircle className="h-3 w-3" />
                      {source}
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="flex items-center justify-between pt-1">
                {locationData.flags.length > 0 ? (
                  <div className="flex items-center gap-2 text-sm text-amber-600">
                    <AlertTriangle className="h-4 w-4" />
                    <span>{locationData.flags.length} flag{locationData.flags.length !== 1 ? 's' : ''}</span>
                  </div>
                ) : (
                  <span />
                )}
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      );
    }

    // Special rendering for completed Test Verification
    if (key === 'test_verification' && isReady && testVerificationData) {
      const isComplete = testVerificationData.status === 'complete';
      const hasMissing = testVerificationData.total_missing > 0;
      const pageNotFound = testVerificationData.status === 'requirements_page_not_found';

      return (
        <Card 
          key={key} 
          className="cursor-pointer transition-all hover:shadow-soft border-slate-200"
          onClick={() => handleCardClick(key)}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100">
                <ClipboardCheck className={`h-5 w-5 ${pageNotFound ? 'text-slate-400' : isComplete ? 'text-teal-600' : 'text-amber-600'}`} />
              </div>
              <div>
                <CardTitle className="text-base">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground">{config.description}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pageNotFound ? (
                <div className="flex items-center gap-2 text-slate-500">
                  <AlertCircle className="h-5 w-5" />
                  <span className="text-sm">Requirements page not found</span>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <span className="text-2xl font-bold text-foreground">{testVerificationData.total_required}</span>
                      <p className="text-xs text-muted-foreground">Required</p>
                    </div>
                    <div className="h-8 w-px bg-slate-200" />
                    <div className="text-center">
                      <span className="text-2xl font-bold text-teal-600">{testVerificationData.total_found}</span>
                      <p className="text-xs text-muted-foreground">Found</p>
                    </div>
                    {hasMissing && (
                      <>
                        <div className="h-8 w-px bg-slate-200" />
                        <div className="text-center">
                          <span className="text-2xl font-bold text-red-600">{testVerificationData.total_missing}</span>
                          <p className="text-xs text-muted-foreground">Missing</p>
                        </div>
                      </>
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between pt-1">
                    {hasMissing ? (
                      <div className="flex items-center gap-2 text-sm text-red-600">
                        <AlertTriangle className="h-4 w-4" />
                        <span>{testVerificationData.total_missing} test{testVerificationData.total_missing !== 1 ? 's' : ''} missing</span>
                      </div>
                    ) : (
                      <span className="text-sm text-teal-600 flex items-center gap-1">
                        <CheckCircle2 className="h-4 w-4" />
                        All required tests present
                      </span>
                    )}
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      );
    }

    // Default card rendering (for processing, pending, or ready without special data)
    return (
      <Card 
        key={key}
        className={`transition-all border-slate-200 ${canClick ? 'cursor-pointer hover:shadow-soft' : ''}`}
        onClick={canClick ? () => handleCardClick(key) : undefined}
      >
        <CardHeader className="pt-4 px-6 pb-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg shrink-0 ${statusConfig.bg}`}>
                <Icon className={`h-5 w-5 ${statusConfig.color}`} />
              </div>
              <div className="min-w-0">
                <CardTitle className="text-base leading-snug">{config.label}</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">{config.description}</p>
              </div>
            </div>
            <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${statusConfig.color}`}>
              <StatusIcon className={`h-3.5 w-3.5 ${statusConfig.animate ? 'animate-spin' : ''}`} />
              {statusConfig.label}
            </span>
          </div>
        </CardHeader>
        {canClick && (
          <CardContent className="pt-0">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>View details</span>
              <ArrowRight className="h-4 w-4" />
            </div>
          </CardContent>
        )}
      </Card>
    );
  };

  // Check if we have any pipelines or are starting processing
  const hasPipelines = pipelineKeys.length > 0;
  const showProcessingState = isProcessingStarted && !hasPipelines;

  return (
    <div className="space-y-6">
      {/* Processing Started Alert - Show immediately when Process All is clicked */}
      {showProcessingState && (
        <div className="flex items-center gap-3 p-4 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="p-2 bg-white rounded-lg border border-primary/20">
            <Loader2 className="h-5 w-5 text-primary animate-spin" />
          </div>
          <div>
            <p className="font-medium text-foreground">Starting processing...</p>
            <p className="text-sm text-muted-foreground">Analysis pipelines are being initialized</p>
          </div>
        </div>
      )}

      {/* Pipeline Cards */}
      {hasPipelines && (
        <div className="space-y-4">
          {/* Risk Assessment - Hero Card (if available) */}
          {pipelineDetails.risk && (
            <div>
              {renderPipelineCard('risk', pipelineDetails.risk)}
            </div>
          )}

          {/* MER & Pathology - Document Analysis Cards */}
          {(pipelineDetails.mer || pipelineDetails.pathology) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pipelineDetails.mer && renderPipelineCard('mer', pipelineDetails.mer)}
              {pipelineDetails.pathology && renderPipelineCard('pathology', pipelineDetails.pathology)}
            </div>
          )}

          {/* Face Match, Location & Test Verification - Verification Cards */}
          {(pipelineDetails.face_match || pipelineDetails.location_check || pipelineDetails.test_verification) && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {pipelineDetails.face_match && renderPipelineCard('face_match', pipelineDetails.face_match)}
              {pipelineDetails.location_check && renderPipelineCard('location_check', pipelineDetails.location_check)}
              {pipelineDetails.test_verification && renderPipelineCard('test_verification', pipelineDetails.test_verification)}
            </div>
          )}
        </div>
      )}

      {/* Empty State - No pipelines yet */}
      {!hasPipelines && !showProcessingState && (
        <Card className="border-dashed">
          <CardContent className="py-12">
            <div className="text-center">
              <div className="mx-auto w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                <FileText className="h-6 w-6 text-slate-400" />
              </div>
              <h3 className="font-medium text-foreground mb-1">No Analysis Yet</h3>
              <p className="text-sm text-muted-foreground">
                Upload documents and process them to see insights here
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Case Recommendation */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Case Recommendation</CardTitle>
              <p className="text-sm text-muted-foreground">Set the underwriting recommendation for this case</p>
            </div>
            {caseData.decision && getCaseDecisionBadge(caseData.decision)}
          </div>
        </CardHeader>
        <CardContent>
          {caseData.decision && caseData.decision !== 'review' ? (
            <div className="space-y-3">
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-sm">
                  <span className="font-medium">Status: </span>
                  {caseData.decision === 'approved'
                    ? 'This case has been approved for underwriting.'
                    : 'This case has been declined.'}
                </p>
                {caseData.decision_at && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Decision made: {formatDateTime(caseData.decision_at)}
                  </p>
                )}
                {caseData.decision_comment && (
                  <p className="text-sm mt-2 pt-2 border-t border-slate-200">
                    <span className="font-medium">Comment: </span>
                    {caseData.decision_comment}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {caseData.decision === 'review' && (
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                  <p className="text-sm">
                    <span className="font-medium">Status: </span>
                    This case requires additional review. You can set a final decision below when ready.
                  </p>
                  {caseData.decision_at && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Marked for review: {formatDateTime(caseData.decision_at)}
                    </p>
                  )}
                  {caseData.decision_comment && (
                    <p className="text-sm mt-2 pt-2 border-t border-slate-200">
                      <span className="font-medium">Comment: </span>
                      {caseData.decision_comment}
                    </p>
                  )}
                </div>
              )}
              {/* Comments Textarea - Always Visible */}
              <div className="space-y-2">
                <label htmlFor="decision-comment" className="text-sm font-medium">
                  Comments <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <textarea
                  id="decision-comment"
                  value={decisionComment}
                  onChange={(e) => setDecisionComment(e.target.value)}
                  placeholder="Add notes or reasoning for your recommendation..."
                  rows={3}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                  disabled={isSettingDecision}
                />
              </div>
              
              {/* Decision Buttons */}
              <div className="flex flex-wrap gap-3">
                <Button
                  size="lg"
                  className="bg-teal-600 hover:bg-teal-700"
                  onClick={() => handleSetDecision('approved')}
                  disabled={isSettingDecision}
                >
                  <ThumbsUp className="h-5 w-5 mr-2" />
                  Approve
                </Button>
                <Button
                  size="lg"
                  variant="default"
                  onClick={() => handleSetDecision('review')}
                  disabled={isSettingDecision}
                >
                  <Eye className="h-5 w-5 mr-2" />
                  Needs Review
                </Button>
                <Button
                  size="lg"
                  variant="destructive"
                  onClick={() => handleSetDecision('declined')}
                  disabled={isSettingDecision}
                >
                  <ThumbsDown className="h-5 w-5 mr-2" />
                  Decline
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
