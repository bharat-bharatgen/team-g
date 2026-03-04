import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { SignupForm } from '@/components/auth/SignupForm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export const SignupPage = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-auth-gradient px-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="flex flex-col items-center mb-8">
          <img 
            src="/bharatgen-logo-circular.png" 
            alt="BharatGen" 
            className="h-16 w-16 mb-3"
          />
          <h1 className="text-2xl font-bold text-bharatgen-blue">InsureCopilot</h1>
          <p className="text-sm text-muted-foreground">by BharatGen</p>
        </div>

        <Card className="shadow-soft border-slate-200/60">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-2xl text-bharatgen-blue">Create an account</CardTitle>
            <CardDescription className="text-base">
              Enter your details to get started with insurance underwriting
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <SignupForm />
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground mt-6">
          AI-Powered Insurance Underwriting
        </p>
      </div>
    </div>
  );
};
