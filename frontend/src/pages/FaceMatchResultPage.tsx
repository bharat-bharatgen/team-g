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
  User,
  CreditCard
} from 'lucide-react';
import { faceMatchService } from '@/services/face-match.service';
import { FaceMatchResultResponse } from '@/types/case.types';
import { formatDateTime } from '@/utils/formatters';
import { DocumentPreview } from '@/components/DocumentPreview';

export const FaceMatchResultPage = () => {
  const { id: caseId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [faceMatchData, setFaceMatchData] = useState<FaceMatchResultResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewComment, setReviewComment] = useState('');

  useEffect(() => {
    fetchData();
  }, [caseId]);

  const fetchData = async () => {
    if (!caseId) return;

    try {
      setIsLoading(true);
      setError(null);
      const response = await faceMatchService.getResult(caseId);
      console.log('Face Match Result:', response);
      setFaceMatchData(response);
    } catch (err: any) {
      console.error('Error fetching face match result:', err);
      setError(err.response?.data?.detail || 'Failed to load face match result');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReview = async (status: 'approved' | 'rejected') => {
    if (!caseId || !faceMatchData) return;

    try {
      setIsReviewing(true);
      await faceMatchService.reviewResult(caseId, {
        status,
        comment: reviewComment || undefined,
      });
      
      // Refresh data
      await fetchData();
      setReviewComment('');
    } catch (err: any) {
      console.error('Error reviewing face match:', err);
      setError(err.response?.data?.detail || 'Failed to review face match');
    } finally {
      setIsReviewing(false);
    }
  };

  const getMatchBadgeVariant = (_match: boolean, matchPercent: number) => {
    if (matchPercent >= 85) return 'success';
    if (matchPercent >= 75) return 'default';
    return 'destructive';
  };

  const getReviewStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: { variant: 'outline', icon: AlertCircle, label: 'Pending Review' },
      approved: { variant: 'success', icon: CheckCircle, label: 'Approved' },
      rejected: { variant: 'destructive', icon: XCircle, label: 'Rejected' },
    };
    
    const config = variants[status] || variants.pending;
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
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loading text="Loading face match result..." />
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

  if (!faceMatchData) {
    return (
      <div className="container mx-auto py-6 space-y-4">
        <Button variant="ghost" onClick={() => navigate(`/cases/${caseId}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Review
        </Button>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>No face match result found</AlertDescription>
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
          <h1 className="text-lg font-semibold">Face Match</h1>
          <Badge variant="secondary" className="text-xs">v{faceMatchData.version}</Badge>
        </div>
        {getReviewStatusBadge(faceMatchData.review_status)}
      </div>

      {/* Match Result Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center justify-between">
            <span>Match Summary</span>
            <Badge 
              variant={getMatchBadgeVariant(faceMatchData.match, faceMatchData.match_percent)}
              className="text-lg px-4 py-1"
            >
              {faceMatchData.match_percent}% Match
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Decision</p>
              <p className="font-semibold capitalize">{faceMatchData.decision.replace('_', ' ')}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Processed At</p>
              <p className="font-semibold">{formatDateTime(faceMatchData.created_at)}</p>
            </div>
          </div>

          {faceMatchData.review_status !== 'pending' && (
            <div className="border-t pt-4 space-y-2">
              <p className="text-sm font-medium">Review Details</p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Reviewed By</p>
                  <p>{faceMatchData.reviewed_by || '-'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Reviewed At</p>
                  <p>{faceMatchData.reviewed_at ? formatDateTime(faceMatchData.reviewed_at) : '-'}</p>
                </div>
              </div>
              {faceMatchData.review_comment && (
                <div>
                  <p className="text-muted-foreground">Comment</p>
                  <p className="text-sm">{faceMatchData.review_comment}</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Side-by-Side Document Comparison (images or PDFs) */}
      <div className="grid grid-cols-2 gap-6">
        {/* Photo (Selfie) */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3 bg-blue-50">
            <CardTitle className="text-sm flex items-center gap-2">
              <User className="h-4 w-4" />
              Geo-tagged Photo (Selfie)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DocumentPreview
              url={faceMatchData.photo_url}
              alt="Geo-tagged Photo"
              downloadFileName="photo"
              minHeight="500px"
            />
          </CardContent>
        </Card>

        {/* ID Proof */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3 bg-green-50">
            <CardTitle className="text-sm flex items-center gap-2">
              <CreditCard className="h-4 w-4" />
              ID Proof Document
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DocumentPreview
              url={faceMatchData.id_url}
              alt="ID Proof"
              downloadFileName="id_proof"
              minHeight="500px"
            />
          </CardContent>
        </Card>
      </div>

      {/* Review Actions */}
      {faceMatchData.review_status === 'pending' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Review Face Match</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Comment (Optional)</label>
              <textarea
                className="w-full mt-2 p-3 border rounded-md resize-none"
                rows={3}
                placeholder="Add a comment about your review decision..."
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
              />
            </div>
            
            <div className="flex gap-3">
              <Button
                variant="default"
                className="flex-1 bg-green-600 hover:bg-green-700"
                onClick={() => handleReview('approved')}
                disabled={isReviewing}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Approve Match
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={() => handleReview('rejected')}
                disabled={isReviewing}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject Match
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
