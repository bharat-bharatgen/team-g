import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { riskService } from '@/services/risk.service';
import { RiskResultResponse, CitedItem } from '@/types/case.types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, AlertTriangle, Info, AlertCircle, ExternalLink, ShieldAlert, Stethoscope, FileText, FlaskConical, Download } from 'lucide-react';
import { API_BASE_URL, RISK_LEVEL_COLORS, RISK_LEVEL_LABELS, STORAGE_KEYS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatters';

export const RiskAnalysisPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [riskData, setRiskData] = useState<RiskResultResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRiskAnalysis();
  }, [id]);

  const fetchRiskAnalysis = async () => {
    if (!id) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await riskService.getResult(id);
      console.log('Risk Analysis Data:', data);
      setRiskData(data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError('Risk analysis not available yet. Processing may still be in progress.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load risk analysis');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadExcel = async () => {
    if (!id) return;

    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      const version = riskData?.version ? `?version=${riskData.version}` : '';
      const url = `${API_BASE_URL}/cases/${id}/risk/export-excel${version}`;

      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `RiskAnalysis_${id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const getRiskLevelBadge = (level: string) => {
    const colorClass = RISK_LEVEL_COLORS[level as keyof typeof RISK_LEVEL_COLORS] || 'bg-gray-100 text-gray-800 border-gray-200';
    const label = RISK_LEVEL_LABELS[level as keyof typeof RISK_LEVEL_LABELS] || level;
    return (
      <Badge className={`${colorClass} border px-4 py-1.5 text-base font-semibold`}>
        {label}
      </Badge>
    );
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'High':
        return <AlertTriangle className="h-6 w-6 text-red-600" />;
      case 'Intermediate':
        return <AlertCircle className="h-6 w-6 text-yellow-600" />;
      case 'Low':
        return <Info className="h-6 w-6 text-green-600" />;
      default:
        return <Info className="h-6 w-6 text-gray-600" />;
    }
  };

  // Navigate to source document based on reference
  const handleCitationClick = (refId: string) => {
    if (!riskData?.references) return;

    const refInfo = riskData.references[refId];
    if (!refInfo) return;

    if (refInfo.source === 'pathology') {
      // Navigate to pathology page with highlight and page params
      const page = refInfo.page || 1;
      navigate(`/cases/${id}/pathology-results?highlight=${encodeURIComponent(refInfo.param || '')}&page=${page}&from=risk`);
    } else if (refInfo.source === 'mer') {
      // Navigate to MER page with page and field params
      const page = refInfo.page || 1;
      const field = refInfo.field || '';
      navigate(`/cases/${id}/mer-results?page=${page}&field=${encodeURIComponent(field)}&from=risk`);
    }
  };

  // Render citation badge
  const renderCitationBadge = (refId: string) => {
    const refInfo = riskData?.references?.[refId];
    if (!refInfo) return null;

    // Create a short label
    let label = refId;
    if (refInfo.source === 'pathology' && refInfo.param) {
      label = refInfo.param;
    } else if (refInfo.source === 'mer') {
      // Format: P1:Q3a or just P1
      const page = refInfo.page ? `P${refInfo.page}` : '';
      const field = refInfo.field ? `:${refInfo.field}` : '';
      label = `MER ${page}${field}`;
    }

    return (
      <Badge
        key={refId}
        variant="outline"
        className="cursor-pointer hover:bg-primary/10 transition-colors text-xs ml-1"
        onClick={(e) => {
          e.stopPropagation();
          handleCitationClick(refId);
        }}
      >
        {label}
        <ExternalLink className="h-3 w-3 ml-1" />
      </Badge>
    );
  };

  // Render cited item (handles both string and object format)
  const renderCitedItem = (item: CitedItem | string, idx: number, bgClass: string, textClass: string, iconClass: string, Icon: any) => {
    // Handle string format (old data)
    if (typeof item === 'string') {
      return (
        <li key={idx} className={`flex items-start gap-3 p-3 ${bgClass} rounded-lg`}>
          <Icon className={`h-5 w-5 ${iconClass} flex-shrink-0 mt-0.5`} />
          <span className={`text-sm ${textClass}`}>{item}</span>
        </li>
      );
    }

    // Handle object format (new data with citations)
    return (
      <li key={idx} className={`flex items-start gap-3 p-3 ${bgClass} rounded-lg`}>
        <Icon className={`h-5 w-5 ${iconClass} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <span className={`text-sm ${textClass}`}>{item.text}</span>
          {item.refs && item.refs.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {item.refs.map((refId) => renderCitationBadge(refId))}
            </div>
          )}
        </div>
      </li>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loading text="Loading risk analysis..." />
      </div>
    );
  }

  if (error || !riskData) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error || 'Risk analysis not found'}</AlertDescription>
        </Alert>
        <div className="flex gap-3 mt-4">
          <Button variant="outline" onClick={() => navigate(`/cases/${id}`)}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Case
          </Button>
          <Button onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const { llm_response, critical_flags, contradictions, based_on } = riskData;
  const isNewFormat = !!llm_response.integrity_concerns;

  const getSeverityBadge = (severity: string) => {
    const styles: Record<string, string> = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      moderate: 'bg-amber-100 text-amber-800 border-amber-300',
      mild: 'bg-blue-100 text-blue-800 border-blue-300',
    };
    return (
      <Badge variant="outline" className={`text-xs ${styles[severity] || ''}`}>
        {severity}
      </Badge>
    );
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0 pb-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/cases/${id}`)}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <span className="text-muted-foreground">|</span>
          <h1 className="text-lg font-semibold">Risk Assessment</h1>
          <Badge variant="secondary" className="text-xs">v{riskData.version}</Badge>
          {isNewFormat && llm_response.risk_score && (
            <Badge variant="outline" className="text-xs font-mono">
              Score: {llm_response.risk_score}/10
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleDownloadExcel}>
            <Download className="h-4 w-4" />
          </Button>
          {getRiskLevelBadge(llm_response.risk_level)}
        </div>
      </div>

      {/* Summary Card */}
      <Card className="border-2">
        <CardHeader>
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-primary/10">
              {getRiskIcon(llm_response.risk_level)}
            </div>
            <div className="flex-1">
              <CardTitle className="text-2xl mb-2">
                {isNewFormat && llm_response.applicant ? llm_response.applicant : 'Summary'}
              </CardTitle>
              <CardDescription className="text-base">
                {based_on.mer_version && `MER v${based_on.mer_version}`}
                {based_on.pathology_version && ` • Pathology v${based_on.pathology_version}`}
                {!based_on.mer_version && !based_on.pathology_version && 'No source data'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {typeof llm_response.summary === 'object' && llm_response.summary !== null ? (
            <div className="space-y-2">
              <div className="flex items-start gap-3 p-3 bg-white rounded-lg border border-primary/20">
                <FileText className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-primary uppercase tracking-wide">MER Findings</span>
                  <p className="text-sm text-foreground mt-0.5">{llm_response.summary.mer}</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-white rounded-lg border border-primary/20">
                <FlaskConical className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-semibold text-primary uppercase tracking-wide">Pathology Findings</span>
                  <p className="text-sm text-foreground mt-0.5">{llm_response.summary.pathology}</p>
                </div>
              </div>
              <div className={`flex items-start gap-3 p-3 rounded-lg border ${
                llm_response.risk_level === 'High' ? 'bg-red-50 border-red-200' :
                llm_response.risk_level === 'Intermediate' ? 'bg-amber-50 border-amber-200' :
                'bg-green-50 border-green-200'
              }`}>
                <AlertCircle className={`h-5 w-5 flex-shrink-0 mt-0.5 ${
                  llm_response.risk_level === 'High' ? 'text-red-600' :
                  llm_response.risk_level === 'Intermediate' ? 'text-amber-600' :
                  'text-green-600'
                }`} />
                <div>
                  <span className={`text-xs font-semibold uppercase tracking-wide ${
                    llm_response.risk_level === 'High' ? 'text-red-700' :
                    llm_response.risk_level === 'Intermediate' ? 'text-amber-700' :
                    'text-green-700'
                  }`}>Conclusion</span>
                  <p className="text-sm font-medium text-foreground mt-0.5">{llm_response.summary.conclusion}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm leading-relaxed bg-secondary/30 p-4 rounded-xl font-medium">
              {llm_response.summary || 'No summary available'}
            </p>
          )}
        </CardContent>
      </Card>

      {/* ─── New Format (v2) ─── */}
      {isNewFormat && (
        <>
          {/* Integrity Concerns */}
          {llm_response.integrity_concerns && llm_response.integrity_concerns.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-red-700">
                  <ShieldAlert className="h-5 w-5" />
                  Integrity Concerns ({llm_response.integrity_concerns.length})
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground">
                  Knowingly concealed behaviors or known events
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {llm_response.integrity_concerns.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-red-300">
                      <ShieldAlert className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <span className="text-sm text-foreground">{item.flag}</span>
                        <div className="mt-2 flex flex-wrap gap-1">
                          {item.mer_ref && renderCitationBadge(item.mer_ref)}
                          {item.path_ref && renderCitationBadge(item.path_ref)}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Clinical Discoveries */}
          {llm_response.clinical_discoveries && llm_response.clinical_discoveries.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-amber-700">
                  <Stethoscope className="h-5 w-5" />
                  Clinical Discoveries ({llm_response.clinical_discoveries.length})
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground">
                  Conditions found via examination — applicant may not have been aware
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {llm_response.clinical_discoveries.map((item, idx) => {
                    const borderClass = item.severity === 'critical' ? 'border-red-300' :
                                       item.severity === 'moderate' ? 'border-amber-300' :
                                       'border-primary/20';
                    return (
                      <li key={idx} className={`flex items-start gap-3 p-3 rounded-lg bg-white border ${borderClass}`}>
                        <Stethoscope className={`h-5 w-5 flex-shrink-0 mt-0.5 ${
                          item.severity === 'critical' ? 'text-red-600' :
                          item.severity === 'moderate' ? 'text-amber-600' : 'text-primary'
                        }`} />
                        <div className="flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-sm text-foreground">{item.finding}</span>
                            {getSeverityBadge(item.severity)}
                          </div>
                          {item.refs && item.refs.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {item.refs.map((refId) => renderCitationBadge(refId))}
                            </div>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Abnormal Labs removed — raw lab data is in Pathology Results page */}
        </>
      )}

      {/* ─── Old Format (v1) ─── */}
      {!isNewFormat && (
        <>
          {/* Red Flags */}
          {llm_response.red_flags && llm_response.red_flags.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-red-700">
                  <AlertTriangle className="h-5 w-5" />
                  Red Flags ({llm_response.red_flags.length})
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground">
                  Click on citation badges to view source documents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {llm_response.red_flags.map((flag, idx) => 
                    renderCitedItem(flag, idx, 'bg-red-50 border-red-200', 'text-red-900', 'text-red-600', AlertTriangle)
                  )}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Contradictions from LLM */}
          {llm_response.contradictions && llm_response.contradictions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-orange-700">
                  <AlertCircle className="h-5 w-5" />
                  Contradictions Identified ({llm_response.contradictions.length})
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground">
                  Click on citation badges to view source documents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {llm_response.contradictions.map((contradiction, idx) => 
                    renderCitedItem(contradiction, idx, 'bg-orange-50 border-orange-200', 'text-orange-900', 'text-orange-600', AlertCircle)
                  )}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Critical Flags (Pre-processing) — shown for both formats */}
      {critical_flags && critical_flags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Critical Values Detected
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {critical_flags.map((flag, idx) => (
                <div key={idx} className="flex items-start gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm">{flag.parameter}</span>
                      <Badge variant="outline" className="text-xs">
                        {flag.source}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Value: <span className="font-semibold">{flag.value}</span>
                    </p>
                    <p className="text-sm mt-1">{flag.message}</p>
                    {flag.severity && (
                      <Badge variant="outline" className="mt-2 text-xs">
                        Severity: {flag.severity}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Contradictions (Pre-processing) — shown for both formats */}
      {contradictions && contradictions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Data Contradictions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {contradictions.map((contradiction, idx) => (
                <div key={idx} className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm capitalize">{contradiction.field?.replace(/_/g, ' ')}</span>
                    <Badge variant="outline" className="text-xs capitalize">
                      {contradiction.type?.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {contradiction.mer_value && (
                      <div>
                        <p className="text-muted-foreground text-xs">MER Value</p>
                        <p className="font-medium">{contradiction.mer_value}</p>
                      </div>
                    )}
                    {contradiction.pathology_value && (
                      <div>
                        <p className="text-muted-foreground text-xs">Pathology Value</p>
                        <p className="font-medium">{contradiction.pathology_value}</p>
                      </div>
                    )}
                  </div>
                  {contradiction.severity && (
                    <Badge variant="destructive" className="mt-2 text-xs">
                      {contradiction.severity} severity
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Analysis Metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Version</p>
              <p className="font-medium">{riskData.version}</p>
            </div>
            <div>
              <p className="text-muted-foreground">MER Version</p>
              <p className="font-medium">{based_on.mer_version || 'N/A'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Pathology Version</p>
              <p className="font-medium">{based_on.pathology_version || 'N/A'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Generated At</p>
              <p className="font-medium">{formatDateTime(riskData.created_at)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button variant="outline" onClick={() => navigate(`/cases/${id}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Case
        </Button>
        <Button variant="outline" onClick={() => navigate('/dashboard')}>
          Dashboard
        </Button>
      </div>
    </div>
  );
};
