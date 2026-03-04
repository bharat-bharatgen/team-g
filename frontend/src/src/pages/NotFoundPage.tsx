import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { FileQuestion, Home } from 'lucide-react';

export const NotFoundPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <Card className="max-w-md w-full">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="bg-slate-100 p-4 rounded-full mb-4">
            <FileQuestion className="h-12 w-12 text-slate-400" />
          </div>
          <h1 className="text-2xl font-bold mb-2">Page Not Found</h1>
          <p className="text-muted-foreground text-center mb-6">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <Button onClick={() => navigate('/dashboard')}>
            <Home className="h-4 w-4 mr-2" />
            Go to Dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
