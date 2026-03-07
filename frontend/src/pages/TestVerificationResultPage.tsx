import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loading } from '@/components/ui/loading';
import { 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ClipboardCheck,
  FileText,
  AlertTriangle,
  Download,
} from 'lucide-react';
import { testVerificationService } from '@/services/test-verification.service';
import { TestVerificationResultResponse } from '@/types/case.types';
import { API_BASE_URL, STORAGE_KEYS } from '@/utils/constants';
import { formatDateTime } from '@/utils/formatters';

export const TestVerificationResultPage = () => {
  const { id: caseId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<TestVerificationResultResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [caseId]);

  const fetchData = async () => {
    if (!caseId) return;

    try {
      setIsLoading(true);
      setError(null);
      const response = await testVerificationService.getResult(caseId);
      setData(response);
    } catch (err: any) {
      console.error('Error fetching test verification result:', err);
      setError(err.response?.data?.detail || 'Failed to load test verification result');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadExcel = async () => {
    if (!caseId) return;

    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      const url = `${API_BASE_URL}/cases/${caseId}/test-verification/export-excel`;

      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `TestVerification_${caseId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: "default" | "destructive" | "outline" | "secondary" | "success"; icon: typeof CheckCircle; label: string }> = {
      complete: { variant: 'success', icon: CheckCircle, label: 'Complete' },
      missing_tests: { variant: 'destructive', icon: AlertTriangle, label: 'Missing Tests' },
      requirements_page_not_found: { variant: 'secondary', icon: AlertCircle, label: 'Page Not Found' },
      extraction_failed: { variant: 'destructive', icon: XCircle, label: 'Extraction Failed' },
    };
    
    const config = variants[status] || { variant: 'secondary' as const, icon: AlertCircle, label: status };
    const Icon = config.icon;
    
    return (
      <Badge variant={config.variant} className="gap-1 text-lg px-4 py-1">
        <Icon className="h-4 w-4" />
        {config.label}
      </Badge>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loading text="Loading test verification result..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-6 space-y-4">
        <Button variant="ghost" onClick={() => navigate(`/cases/${caseId}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Review
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container mx-auto py-6 space-y-4">
        <Button variant="ghost" onClick={() => navigate(`/cases/${caseId}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Review
        </Button>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>No test verification result found</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header - compact, aligned with MER/Pathology */}
      <div className="flex items-center justify-between flex-shrink-0 pb-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/cases/${caseId}`)}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <span className="text-muted-foreground">|</span>
          <h1 className="text-lg font-semibold">Test Requirements</h1>
          <Badge variant="secondary" className="text-xs">v{data.version}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleDownloadExcel}>
            <Download className="h-4 w-4" />
          </Button>
          {getStatusBadge(data.status)}
        </div>
      </div>

      {/* Summary Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <ClipboardCheck className="h-5 w-5" />
            Verification Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {data.status === 'requirements_page_not_found' ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Insurance requirements page (Page 5) was not found in the uploaded documents.
              </AlertDescription>
            </Alert>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <p className="text-3xl font-bold text-foreground">{data.total_required}</p>
                  <p className="text-sm text-muted-foreground">Required Tests</p>
                </div>
                <div className="text-center p-4 bg-teal-50 rounded-lg">
                  <p className="text-3xl font-bold text-teal-600">{data.total_found}</p>
                  <p className="text-sm text-muted-foreground">Found</p>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <p className="text-3xl font-bold text-red-600">{data.total_missing}</p>
                  <p className="text-sm text-muted-foreground">Missing</p>
                </div>
                <div className="text-center p-4 bg-slate-50 rounded-lg">
                  <p className="text-3xl font-bold text-foreground">
                    {data.total_required > 0 ? Math.round((data.total_found / data.total_required) * 100) : 0}%
                  </p>
                  <p className="text-sm text-muted-foreground">Complete</p>
                </div>
              </div>

              {data.total_missing > 0 && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {data.total_missing} required test{data.total_missing !== 1 ? 's are' : ' is'} missing: {data.missing_tests.join(', ')}
                  </AlertDescription>
                </Alert>
              )}

              {data.total_missing === 0 && data.total_required > 0 && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    All required tests are present in the pathology report.
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}

          <div className="grid grid-cols-2 gap-4 pt-4 border-t text-sm">
            <div>
              <p className="text-muted-foreground">Processed At</p>
              <p className="font-medium">{formatDateTime(data.created_at)}</p>
            </div>
            {data.extraction_confidence > 0 && (
              <div>
                <p className="text-muted-foreground">Extraction Confidence</p>
                <p className="font-medium">{Math.round(data.extraction_confidence * 100)}%</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Extracted Requirements */}
      {data.page_found && data.ins_test_remark && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Extracted Requirements
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {data.proposal_number && (
                <div>
                  <p className="text-sm text-muted-foreground">Proposal Number</p>
                  <p className="font-medium">{data.proposal_number}</p>
                </div>
              )}
              {data.life_assured_name && (
                <div>
                  <p className="text-sm text-muted-foreground">Life Assured</p>
                  <p className="font-medium">{data.life_assured_name}</p>
                </div>
              )}
            </div>
            
            <div>
              <p className="text-sm text-muted-foreground mb-2">Insurance Test Remark</p>
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="font-mono text-sm">{data.ins_test_remark}</p>
              </div>
            </div>

            {data.raw_requirements.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">Parsed Categories</p>
                <div className="flex flex-wrap gap-2">
                  {data.raw_requirements.map((req, idx) => (
                    <Badge key={idx} variant="outline">{req}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Required Tests Table */}
      {data.required_tests.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Required Tests</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">Category</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">Test Name</th>
                    <th className="text-center px-4 py-3 text-sm font-medium text-muted-foreground">Status</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-muted-foreground">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.required_tests.map((test, idx) => (
                    <tr key={idx} className={test.found ? '' : 'bg-red-50'}>
                      <td className="px-4 py-3 text-sm">{test.category}</td>
                      <td className="px-4 py-3 text-sm font-medium">{test.test_name}</td>
                      <td className="px-4 py-3 text-center">
                        {test.found ? (
                          <CheckCircle className="h-5 w-5 text-teal-600 mx-auto" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600 mx-auto" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {test.pathology_value || (test.found ? 'Present' : 'Not Found')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
