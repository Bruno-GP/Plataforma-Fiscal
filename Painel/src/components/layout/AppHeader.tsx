import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const nomeExibicao = user?.name?.trim() || 'Empresa';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0E1525] text-white">
      <div className="flex min-h-14 w-full flex-wrap items-center gap-2 px-4 py-2 md:flex-nowrap">

        <SidebarTrigger className="text-white hover:bg-white/10 hover:text-white" />

        {/* ESQUERDA — Empresa / Logo */}
        <div className="shrink-0">
          <span className="block text-sm font-semibold" title={nomeExibicao}>
            {nomeExibicao}
          </span>
        </div>

        {/* DIREITA — Ação */}
        <div className="ml-auto shrink-0">
          <Button
            variant="outline"
            onClick={handleLogout}
            className="border-white/20 text-white hover:bg-white/10"
          >
            <LogOut className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Sair</span>
          </Button>
        </div>

      </div>
    </header>

  );
}
