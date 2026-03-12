import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { caseService } from '@/services/case.service';
import { CaseDashboardResponse, DashboardFilterType } from '@/types/case.types';
import { StatsOverview } from '@/components/dashboard/StatsOverview';
import { CaseList } from '@/components/dashboard/CaseList';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Button } from '@/components/ui/button';
import { Loading, Spinner } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Plus, RefreshCw, AlertCircle, FileText, Sparkles } from 'lucide-react';

const FILTER_OPTIONS: { value: DashboardFilterType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'decided', label: 'Decided' },
  { value: 'attention', label: 'Needs Attention' },
];

const PAGE_SIZE = 100;

export const DashboardPage = () => {
  const navigate = useNavigate();
  
  // Dashboard data state
  const [dashboardData, setDashboardData] = useState<CaseDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') || '1');
  const filter = (searchParams.get('filter') || 'all') as DashboardFilterType;
  
  // New Case Modal State
  const [isNewCaseOpen, setIsNewCaseOpen] = useState(false);
  const [caseName, setCaseName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchDashboard = async (currentFilter: DashboardFilterType = filter, currentPage: number = page) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await caseService.getDashboard(currentFilter, currentPage, PAGE_SIZE);
      setDashboardData(response);
    } catch (err: any) {
      console.error('Error fetching dashboard:', err);
      setError(err.response?.data?.detail || 'Failed to load cases. Make sure backend is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchDashboard(filter, page);
    setIsRefreshing(false);
  };

  const handleFilterChange = async (newFilter: DashboardFilterType) => {
    setSearchParams({ filter: newFilter, page: '1' });
    await fetchDashboard(newFilter, 1);
  };

  const handlePageChange = async (newPage: number) => {
    setSearchParams({ filter, page: String(newPage) });
    await fetchDashboard(filter, newPage);
  };

  const handleCreateCase = async () => {
    if (!caseName.trim()) {
      setCreateError('Please enter a case name');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const newCase = await caseService.createCase(caseName.trim());
      setIsNewCaseOpen(false);
      setCaseName('');
      navigate(`/cases/${newCase.id}?tab=documents`);
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed to create case');
    } finally {
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isCreating) {
      handleCreateCase();
    }
  };

  useEffect(() => {
    fetchDashboard(filter, page);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loading text="Loading cases..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Cases</h1>
          <p className="text-muted-foreground mt-1">
            Manage your insurance underwriting cases
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => setIsNewCaseOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Case
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {dashboardData?.total === 0 && !error ? (
        <EmptyState onCreateCase={() => setIsNewCaseOpen(true)} />
      ) : dashboardData ? (
        <>
          <StatsOverview
            total={dashboardData.total}
            awaitingDecision={dashboardData.awaiting_decision}
            decided={dashboardData.decided}
            needsAttentionCount={dashboardData.needs_attention_count}
            highRiskCount={dashboardData.high_risk_count}
          />
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Cases</h2>
              <div className="flex gap-1 bg-muted p-1 rounded-lg">
                {FILTER_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleFilterChange(option.value)}
                    className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                      filter === option.value
                        ? 'bg-background text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            {dashboardData.cases.length === 0 && dashboardData.filtered_total === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No cases match the current filter.
              </div>
            ) : (
              <CaseList
                cases={dashboardData.cases}
                page={page}
                totalCases={dashboardData.filtered_total}
                pageSize={PAGE_SIZE}
                onPageChange={handlePageChange}
                onCaseDeleted={() => fetchDashboard(filter, page)}
              />
            )}
          </div>
        </>
      ) : null}

      {/* New Case Modal */}
      <Dialog open={isNewCaseOpen} onOpenChange={setIsNewCaseOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2.5 rounded-xl bg-primary/10">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div>
                <DialogTitle className="text-xl">New Case</DialogTitle>
                <DialogDescription className="text-sm">
                  Create a new insurance underwriting case
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          
          <div className="space-y-4 pt-2">
            {createError && (
              <Alert variant="destructive" className="py-2">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{createError}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <label htmlFor="caseName" className="text-sm font-medium">
                Case Name
              </label>
              <input
                id="caseName"
                type="text"
                value={caseName}
                onChange={(e) => setCaseName(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g., John Doe - Life Insurance"
                className="w-full px-4 py-3 border border-input rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                disabled={isCreating}
                autoFocus
                maxLength={100}
              />
              <p className="text-xs text-muted-foreground">
                Enter a descriptive name to identify this case
              </p>
            </div>

            <div className="bg-secondary/30 p-4 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Sparkles className="h-4 w-4 text-primary" />
                What happens next
              </div>
              <ul className="text-sm text-muted-foreground space-y-1.5 ml-6">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full" />
                  Upload documents (MER, Pathology, Photo, ID)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full" />
                  AI extracts and analyzes data
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full" />
                  Review insights and make decision
                </li>
              </ul>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                onClick={handleCreateCase}
                disabled={isCreating}
                className="flex-1"
                size="lg"
              >
                {isCreating ? (
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
                onClick={() => {
                  setIsNewCaseOpen(false);
                  setCaseName('');
                  setCreateError(null);
                }}
                disabled={isCreating}
                size="lg"
              >
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
