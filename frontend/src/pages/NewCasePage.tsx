import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { caseService } from '@/services/case.service';
import { useCaseStore } from '@/store/caseStore';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Spinner } from '@/components/ui/loading';
import { AlertCircle, FileText } from 'lucide-react';

export const NewCasePage = () => {
  const navigate = useNavigate();
  const addCase = useCaseStore((state) => state.addCase);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [caseName, setCaseName] = useState('');

  const handleCreateCase = async () => {
    if (!caseName.trim()) {
      setError('Please enter a case name');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const newCase = await caseService.createCase(caseName.trim());
      addCase(newCase);
      navigate(`/cases/${newCase.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create case');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Create New Case</h1>
        <p className="text-muted-foreground mt-1">
          Start a new insurance underwriting case
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-3 rounded-lg">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <CardTitle>New Insurance Case</CardTitle>
              <CardDescription>
                Create a case to upload documents and get AI-powered underwriting analysis
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="caseName" className="text-sm font-medium">
              Case Name <span className="text-red-500">*</span>
            </label>
            <input
              id="caseName"
              type="text"
              value={caseName}
              onChange={(e) => setCaseName(e.target.value)}
              placeholder="e.g., John Doe - Life Insurance"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              disabled={isLoading}
              maxLength={100}
            />
            <p className="text-xs text-muted-foreground">
              Enter a descriptive name to identify this case
            </p>
          </div>

          <div className="bg-secondary/50 p-4 rounded-lg space-y-2">
            <h3 className="font-medium">What you'll need:</h3>
            <ul className="text-sm text-muted-foreground space-y-1 ml-4 list-disc">
              <li>Medical Examination Report (MER)</li>
              <li>Pathology / Lab Reports</li>
              <li>Geo-tagged Photograph</li>
              <li>ID Proof Document</li>
            </ul>
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleCreateCase}
              disabled={isLoading}
              className="flex-1"
            >
              {isLoading ? (
                <>
                  <Spinner className="mr-2" />
                  Creating...
                </>
              ) : (
                'Create Case'
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate('/dashboard')}
              disabled={isLoading}
            >
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
