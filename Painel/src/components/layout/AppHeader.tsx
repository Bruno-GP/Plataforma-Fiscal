import { ChevronDown, User, Settings, LogOut } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { SidebarTrigger } from '@/components/ui/sidebar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0E1525] text-white">
      <div className="flex h-14 w-full items-center px-4">

        {/* ESQUERDA — Empresa / Logo */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">
            {user?.name ?? 'Empresa'}
          </span>
        </div>

        {/* ESPAÇO FLEXÍVEL */}
        <div className="flex-1" />

        {/* DIREITA — Usuário */}
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 rounded-md px-2 py-1.5 text-white focus:outline-none">
              <Avatar className="h-8 w-8">
                <AvatarImage src={user?.avatar} />
                <AvatarFallback className="bg-[#0E1525] text-white text-sm border border-white/10">
                  {user ? getInitials(user.name) : 'U'}
                </AvatarFallback>
              </Avatar>
              <span className="hidden text-sm font-medium md:block">
                {user?.name}
              </span>
              <ChevronDown className="h-4 w-4 text-white/80" />
            </DropdownMenuTrigger>

            <DropdownMenuContent
              align="end"
              className="w-56 bg-[#0E1525] text-white border border-white/10"
            >
              <div className="flex flex-col px-2 py-1.5">
                <span className="text-sm font-medium">{user?.name}</span>
                <span className="text-xs text-white/60">{user?.email}</span>
              </div>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Sair
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

      </div>
    </header>

  );
}
