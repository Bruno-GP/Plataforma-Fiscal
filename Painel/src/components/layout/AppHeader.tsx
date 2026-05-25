import { Bell, CircleHelp, LogOut, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const nomeExibicao = user?.name?.trim() || 'Empresa';
  const initials = nomeExibicao
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || 'TV';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-700/70 bg-[#08111f]/95 text-slate-100 backdrop-blur">
      <div className="flex min-h-16 w-full flex-wrap items-center gap-3 px-4 py-2 md:flex-nowrap md:px-8">
        <SidebarTrigger className="text-slate-300 hover:bg-slate-800 hover:text-slate-50 md:hidden" />

        <div className="flex shrink-0 items-center gap-3">
          <span className="text-lg font-semibold text-sky-300">TaxVision Pro</span>
          <span className="hidden h-6 w-px bg-slate-700 lg:block" />
          <span className="hidden text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 lg:block">
            Fiscal Analytics
          </span>
        </div>

        <div className="relative order-last w-full md:order-none md:ml-6 md:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <Input
            aria-label="Busca global"
            placeholder="Pesquisar cliente, nota ou documento..."
            className="h-10 border-slate-700/90 bg-slate-950/55 pl-10"
          />
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-2">
          <Button variant="ghost" size="icon" aria-label="Notificacoes" className="relative text-slate-300">
            <Bell className="h-5 w-5" />
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-400 ring-2 ring-[#08111f]" />
          </Button>
          <Button variant="ghost" size="icon" aria-label="Ajuda" className="text-slate-300">
            <CircleHelp className="h-5 w-5" />
          </Button>
          <div className="mx-1 hidden h-8 w-px bg-slate-700 sm:block" />
          <div className="hidden text-right sm:block">
            <p className="max-w-36 truncate text-sm font-semibold text-slate-100" title={nomeExibicao}>
              {nomeExibicao}
            </p>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Master Partner</p>
          </div>
          <Avatar className="h-9 w-9 border border-sky-400/50 bg-slate-900">
            <AvatarFallback className="bg-slate-900 text-xs font-semibold text-sky-200">
              {initials}
            </AvatarFallback>
          </Avatar>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            aria-label="Sair"
            className="text-slate-400 hover:text-rose-300"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
