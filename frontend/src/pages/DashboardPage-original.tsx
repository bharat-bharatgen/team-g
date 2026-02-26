import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { caseService } from '@/services/case.service';
import { CaseDashboardResponse } from '@/types/case.types';
import { StatsOverview } from '@/components/dashboard/StatsOverview';
import { CaseList } from '@/components/dashboard/CaseList';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus, RefreshCw, AlertCircle } from 'lucide-react';

export const DashboardPage = () => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState<CaseDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchCases = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await caseService.getDashboard('all');
      setDashboardData(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load cases');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchCases();
    setIsRefreshing(false);
  };

  useEffect(() => {
    fetchCases();
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
          <h1 className="text-3xl font-bold">Dashboard</h1>
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
          <Button onClick={() => navigate('/cases/new')}>
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

      {!dashboardData || dashboardData.cases.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <StatsOverview
            total={dashboardData.total}
            awaitingDecision={dashboardData.awaiting_decision}
            decided={dashboardData.decided}
            needsAttentionCount={dashboardData.needs_attention_count}
            highRiskCount={dashboardData.high_risk_count}
          />
          <div>
            <h2 className="text-xl font-semibold mb-4">Recent Cases</h2>
            <CaseList cases={dashboardData.cases} />
          </div>
        </>
      )}
    </div>
  );
};
