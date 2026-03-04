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
  MapPin,
  User,
  CreditCard,
  FileText,
  Navigation,
  Ruler
} from 'lucide-react';
import { locationCheckService, LocationCheckResult } from '@/services/location-check.service';
import { formatDateTime } from '@/utils/formatters';
import { DocumentPreview } from '@/components/DocumentPreview';

export const LocationCheckResultPage = () => {
  const { id: caseId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [locationData, setLocationData] = useState<LocationCheckResult | null>(null);
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
      const response = await locationCheckService.getResult(caseId);
      console.log('Location Check Result:', response);
      setLocationData(response);
    } catch (err: any) {
      console.error('Error fetching location check result:', err);
      setError(err.response?.data?.detail || 'Failed to load location check result');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReview = async (status: 'approved' | 'rejected') => {
    if (!caseId || !locationData) return;

    try {
      setIsReviewing(true);
      await locationCheckService.reviewResult(caseId, {
        status,
        comment: reviewComment || undefined,
      });
      
      // Refresh data
      await fetchData();
      setReviewComment('');
    } catch (err: any) {
      console.error('Error reviewing location check:', err);
      setError(err.response?.data?.detail || 'Failed to review location check');
    } finally {
      setIsReviewing(false);
    }
  };

  const getDecisionBadgeVariant = (decision: string) => {
    switch (decision) {
      case 'pass':
        return 'success';
      case 'fail':
        return 'destructive';
      case 'insufficient':
        return 'default';
      default:
        return 'secondary';
    }
  };

  const getDecisionLabel = (decision: string) => {
    switch (decision) {
      case 'pass':
        return 'Pass';
      case 'fail':
        return 'Fail';
      case 'insufficient':
        return 'Insufficient Data';
      default:
        return decision;
    }
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

  const getSourceStatusBadge = (status: string): "default" | "destructive" | "outline" | "secondary" | "success" => {
    const variants: Record<string, "default" | "destructive" | "outline" | "secondary" | "success"> = {
      found: 'success',
      not_found: 'secondary',
      skipped: 'outline',
      geocode_failed: 'destructive',
    };
    return variants[status] || 'secondary';
  };

  const getSourceLabel = (sourceType: string) => {
    const labels: Record<string, string> = {
      photo: 'Geo-tagged Photo',
      id_card: 'ID Card Address',
      lab: 'Lab Address',
    };
    return labels[sourceType] || sourceType;
  };

  const getStatusLabel = (status: string) => {
    if (status === 'geocode_failed') {
      return 'pincode absent';
    }
    return status.replace('_', ' ');
  };

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'photo':
        return User;
      case 'id_card':
        return CreditCard;
      case 'lab':
        return FileText;
      default:
        return MapPin;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loading text="Loading location check result..." />
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

  if (!locationData) {
    return (
      <div className="container mx-auto py-6 space-y-4">
        <Button variant="ghost" onClick={() => navigate(`/cases/${caseId}`)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Review
        </Button>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>No location check result found</AlertDescription>
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
          <h1 className="text-lg font-semibold">Location Verification</h1>
          <Badge variant="secondary" className="text-xs">v{locationData.version}</Badge>
        </div>
        {getReviewStatusBadge(locationData.review_status)}
      </div>

      {/* Decision Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center justify-between">
            <span>Verification Summary</span>
            <Badge 
              variant={getDecisionBadgeVariant(locationData.decision)}
              className="text-lg px-4 py-1"
            >
              {getDecisionLabel(locationData.decision)}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Decision</p>
              <p className="font-semibold capitalize">{getDecisionLabel(locationData.decision)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Sources Detected</p>
              <p className="font-semibold">{locationData.sources_detected.length} of 3</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Processed At</p>
              <p className="font-semibold">{formatDateTime(locationData.created_at)}</p>
            </div>
          </div>

          <Alert variant={locationData.decision === 'fail' ? 'destructive' : 'default'}>
            <MapPin className="h-4 w-4" />
            <AlertDescription>
              {locationData.message}
            </AlertDescription>
          </Alert>

          {locationData.review_status !== 'pending' && (
            <div className="border-t pt-4 space-y-2">
              <p className="text-sm font-medium">Review Details</p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Reviewed By</p>
                  <p>{locationData.reviewed_by || '-'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Reviewed At</p>
                  <p>{locationData.reviewed_at ? formatDateTime(locationData.reviewed_at) : '-'}</p>
                </div>
              </div>
              {locationData.review_comment && (
                <div>
                  <p className="text-muted-foreground">Comment</p>
                  <p className="text-sm">{locationData.review_comment}</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Location Sources */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Navigation className="h-5 w-5" />
            Location Sources
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {locationData.sources.map((source, idx) => {
              const SourceIcon = getSourceIcon(source.source_type);
              return (
                <div key={idx} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <SourceIcon className="h-5 w-5 text-blue-600" />
                      <h4 className="font-semibold">{getSourceLabel(source.source_type)}</h4>
                    </div>
                    <Badge variant={getSourceStatusBadge(source.status)}>
                      {getStatusLabel(source.status)}
                    </Badge>
                  </div>

                  {source.status === 'found' ? (
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      {source.raw_input && (
                        <div>
                          <p className="text-muted-foreground">Raw Input</p>
                          <p className="font-mono text-xs">{source.raw_input}</p>
                        </div>
                      )}
                      {source.address && (
                        <div>
                          <p className="text-muted-foreground">Address</p>
                          <p>{source.address}</p>
                        </div>
                      )}
                      {source.coords && (
                        <div>
                          <p className="text-muted-foreground">Coordinates</p>
                          <p className="font-mono text-xs">
                            {source.coords[0].toFixed(4)}, {source.coords[1].toFixed(4)}
                          </p>
                        </div>
                      )}
                      {source.message && (
                        <div>
                          <p className="text-muted-foreground">Status</p>
                          <p className="text-xs">{source.message}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">{source.message || 'No location data available'}</p>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Distance Analysis */}
      {locationData.distances.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Ruler className="h-5 w-5" />
              Distance Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {locationData.distances.map((dist, idx) => (
                <div 
                  key={idx} 
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    dist.flag ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <MapPin className={`h-5 w-5 ${dist.flag ? 'text-red-600' : 'text-green-600'}`} />
                    <div>
                      <p className="font-medium">
                        {getSourceLabel(dist.source_a)} ↔ {getSourceLabel(dist.source_b)}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Distance: {dist.distance_km.toFixed(2)} km
                      </p>
                    </div>
                  </div>
                  <div>
                    {dist.flag ? (
                      <Badge variant="destructive" className="gap-1">
                        <AlertCircle className="h-3 w-3" />
                        Flagged
                      </Badge>
                    ) : (
                      <Badge variant="success" className="gap-1">
                        <CheckCircle className="h-3 w-3" />
                        Within Threshold
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Side-by-Side Document Viewing (images or PDFs) */}
      <div className="grid grid-cols-2 gap-6">
        {/* Photo */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3 bg-blue-50">
            <CardTitle className="text-sm flex items-center gap-2">
              <User className="h-4 w-4" />
              Geo-tagged Photo
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DocumentPreview
              url={locationData.photo_url}
              alt="Geo-tagged Photo"
              downloadFileName="photo"
              minHeight="400px"
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
              url={locationData.id_url}
              alt="ID Proof"
              downloadFileName="id_proof"
              minHeight="400px"
            />
          </CardContent>
        </Card>
      </div>

      {/* Review Actions */}
      {locationData.review_status === 'pending' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Review Location Check</CardTitle>
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
                Approve
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={() => handleReview('rejected')}
                disabled={isReviewing}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

