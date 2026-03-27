import { AlertTriangle, FileDigit, FileSearch, FileUp, LayoutDashboard, LogOut, Sparkles, Users } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { NavLink } from '@/components/NavLink';
import { Button } from '@/components/ui/button';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';

const menuItemsBase = [
  { title: 'Vendas', url: '/analise-vendas', icon: LayoutDashboard },
  { title: 'Clientes', url: '/analise-clientes', icon: Users },
  // { title: 'Atualizações', url: '/atualizacoes', icon: BellRing },
  // { title: 'Configurações', url: '/configuracoes', icon: Settings },
];

const menuItemImportacaoXml = { title: 'Importação XML', url: '/importacao-xml', icon: FileUp };
const menuItemImportacaoSped = { title: 'Importações SPED', url: '/importacao-sped', icon: FileDigit };
const menuItemAnaliseFiscal = { title: 'Compras', url: '/analise-compras', icon: FileSearch };
const menuItemRelatoriosIA = { title: 'Relatórios com IA', url: '/relatorios-ia', icon: Sparkles };
const menuItemInconsistencias = { title: 'Inconsistencias', url: '/inconsistencias', icon: AlertTriangle };

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const menuItems = user?.tem_sped
    ? [...menuItemsBase, menuItemAnaliseFiscal, menuItemRelatoriosIA, menuItemInconsistencias, menuItemImportacaoSped]
    : [...menuItemsBase, menuItemAnaliseFiscal, menuItemRelatoriosIA, menuItemInconsistencias, menuItemImportacaoXml];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Sidebar
      variant="sidebar"
      collapsible="none"
      className="
        shrink-0
        sticky top-0
        h-svh
        w-56
        bg-[#0E1525]
        text-white
        border-r
        border-white/10
      "
    >
      <SidebarHeader className="gap-3 bg-[#0E1525] p-3">
        <div className="flex items-center justify-between gap-2">
          <div
            className="
              flex min-w-0 items-center rounded-md bg-[#0E1525] text-white text-sm font-semibold
              border border-white/10 overflow-hidden
              px-2.5 py-1.5 w-full
            "
            title={user?.name ?? 'Empresa'}
          >
            <span className="block w-full truncate whitespace-nowrap text-xs">
              {user?.name ?? 'Empresa'}
            </span>

            {/* <span className="hidden text-xs group-data-[collapsible=icon]:block">
              {(user?.name ?? 'E').slice(0, 1).toUpperCase()}
            </span> */}
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="bg-[#0E1525]">
        <SidebarGroup className="px-2.5">
          <SidebarGroupContent className="flex justify-center">
            <SidebarMenu className="w-full">
              {menuItems.map((item) => {
                const isActive = location.pathname === item.url;

                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      size="sm"
                      className="h-9 text-sm hover:bg-transparent hover:text-inherit data-[active=true]:bg-white data-[active=true]:text-[#0E1525] data-[active=true]:hover:bg-white/90 data-[active=true]:hover:text-[#0E1525]"
                      isActive={isActive}
                    >
                      <NavLink
                        to={item.url}
                        className="flex items-center justify-between gap-2 text-sm text-white/80"
                        activeClassName="bg-white text-[#0E1525] hover:bg-white/90"
                      >
                        <span className="flex items-center gap-2">
                          <item.icon className="h-4 w-4" />
                          <span>{item.title}</span>
                        </span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="bg-[#0E1525] p-3">
        <Button
          variant="outline"
          onClick={handleLogout}
          title="Sair"
        >
          <LogOut className="h-4 w-4" />
          <span>Sair</span>
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
