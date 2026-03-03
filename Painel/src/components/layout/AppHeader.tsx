import { FileDigit, FileUp, LayoutDashboard, LogOut, Receipt } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { hasUnreadUpdates } from '../../contexts/updates';

import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { NavLink } from '@/components/NavLink';

const menuItems = [
  { title: 'Dashboard', url: '/dashboard', icon: LayoutDashboard },
  { title: 'Faturamento', url: '/faturamento', icon: Receipt },
  { title: 'Importação XML', url: '/importacao-xml', icon: FileUp },
  { title: 'Importações SPED', url: '/importacao-sped', icon: FileDigit },
  // { title: 'Atualizações', url: '/atualizacoes', icon: BellRing },
  // { title: 'Clientes', url: '/clientes', icon: Users },
  // { title: 'Configurações', url: '/configuracoes', icon: Settings },
]

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const nomeExibicao = user?.name?.trim() || 'Empresa';
  const hasUnreadUpdateLog = hasUnreadUpdates();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0E1525] text-white">
      <div className="flex min-h-14 w-full flex-wrap items-center gap-2 px-4 py-2 md:flex-nowrap">

        {/* ESQUERDA — Empresa / Logo */}
        <div className="shrink-0">
          <span className="block text-sm font-semibold" title={nomeExibicao}>
            {nomeExibicao}
          </span>
        </div>

        <nav className="order-3 flex w-full items-center gap-1 overflow-x-auto pb-1 md:order-none md:w-auto md:flex-1 md:justify-center md:pb-0">
          {menuItems.map((item) => {
            const isUpdatesItem = item.url === '/atualizacoes';
            const isUpdatesActive = location.pathname === '/atualizacoes';

            return (
              <NavLink
                key={item.url}
                to={item.url}
                className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm text-white/80 transition-colors hover:bg-white/10 hover:text-white whitespace-nowrap"
                activeClassName="bg-white/10 text-white"
              >
                <item.icon className="h-4 w-4" />
                <span>{item.title}</span>
                {isUpdatesItem && hasUnreadUpdateLog && !isUpdatesActive && (
                  <span className="rounded-full bg-yellow-400 px-2 py-0.5 text-[10px] font-semibold uppercase text-yellow-950">
                    Novo
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

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
