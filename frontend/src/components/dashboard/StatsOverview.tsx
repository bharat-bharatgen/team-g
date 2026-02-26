import { Card } from '@/components/ui/card';
import { FileText, Clock, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';

interface StatsOverviewProps {
  total: number;
  awaitingDecision: number;
  decided: number;
  needsAttentionCount: number;
  highRiskCount: number;
}

export const StatsOverview = ({
  total,
  awaitingDecision,
  decided,
  needsAttentionCount,
  highRiskCount,
}: StatsOverviewProps) => {
  const statCards = [
    {
      title: 'Total Cases',
      value: total,
      icon: FileText,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Awaiting Decision',
      value: awaitingDecision,
      icon: Clock,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      title: 'Decided',
      value: decided,
      icon: CheckCircle2,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
    },
    {
      title: 'Needs Attention',
      value: needsAttentionCount,
      icon: AlertTriangle,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      title: 'High Risk',
      value: highRiskCount,
      icon: ShieldAlert,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {statCards.map((stat) => (
        <Card key={stat.title} className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
              <p className="text-2xl font-bold">{stat.value}</p>
            </div>
            <div className={`p-2.5 rounded-xl ${stat.bgColor}`}>
              <stat.icon className={`h-5 w-5 ${stat.color}`} />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};
