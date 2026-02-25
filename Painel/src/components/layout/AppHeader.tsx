import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0E1525] text-white">
      <div className="flex h-14 w-full items-center gap-2 px-4">

        {/* ESQUERDA — Empresa / Logo */}
        <div className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold" title={user?.name ?? 'Empresa'}>
            {user?.name ?? 'Empresa'}
          </span>
        </div>

        {/* ESPAÇO FLEXÍVEL
        <div className="flex-1" /> */}

        {/* DIREITA — Ação */}
        <div className="shrink-0">
          <Button
            variant="outline"
            onClick={handleLogout}
            className="text-white border-white/20 hover:bg-white/10"
          >
            <LogOut className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Sair</span>
          </Button>
        </div>

      </div>
    </header>

  );
}
