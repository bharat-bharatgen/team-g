import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FolderOpen, Plus, Sparkles } from 'lucide-react';

interface EmptyStateProps {
  onCreateCase?: () => void;
}

export const EmptyState = ({ onCreateCase }: EmptyStateProps) => {
  return (
    <Card className="border-dashed border-2">
      <CardContent className="flex flex-col items-center justify-center py-16">
        <div className="bg-primary/5 p-5 rounded-2xl mb-5">
          <FolderOpen className="h-14 w-14 text-primary/40" />
        </div>
        <h3 className="text-xl font-semibold mb-2">No cases yet</h3>
        <p className="text-muted-foreground text-center mb-8 max-w-md">
          Get started by creating your first case. Upload documents and let AI handle the
          underwriting analysis.
        </p>
        <Button onClick={onCreateCase} size="lg" className="gap-2">
          <Plus className="h-5 w-5" />
          Create Your First Case
        </Button>
        <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
          <Sparkles className="h-4 w-4" />
          <span>AI-powered analysis in minutes</span>
        </div>
      </CardContent>
    </Card>
  );
};
