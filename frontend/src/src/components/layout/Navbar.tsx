import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { LogOut, User } from 'lucide-react';
import { formatPhoneNumber } from '@/utils/formatters';

export const Navbar = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white/80 backdrop-blur-sm border-b border-slate-200/60 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => navigate('/dashboard')}
          >
            <img 
              src="/bharatgen-logo-circular.png" 
              alt="BharatGen" 
              className="w-9 h-9 transition-transform group-hover:scale-105"
            />
            <div className="flex flex-col">
              <span className="text-lg font-bold text-bharatgen-blue leading-tight">
                InsureCopilot
              </span>
              <span className="text-[10px] text-muted-foreground leading-tight">
                by BharatGen
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {user && (
              <div className="flex items-center gap-2 px-3 py-2 bg-secondary/50 rounded-lg">
                <User className="h-4 w-4 text-primary" />
                <div className="text-sm">
                  <p className="font-medium text-foreground">{user.name || 'User'}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatPhoneNumber(user.phone_number)}
                  </p>
                </div>
              </div>
            )}
            <Button variant="outline" size="sm" onClick={handleLogout} className="hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30">
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
};
