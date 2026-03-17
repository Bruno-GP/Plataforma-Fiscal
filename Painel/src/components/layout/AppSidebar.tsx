import { FileDigit, FileSearch, FileUp, LayoutDashboard, LogOut, Sparkles, Users } from 'lucide-react';
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
  SidebarFooter,
  SidebarTrigger,
  useSidebar
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';

const menuItemsBase = [
  { title: 'Análise de Vendas', url: '/analise-vendas', icon: LayoutDashboard },
  { title: 'Análise de Clientes', url: '/analise-clientes', icon: Users },
  // { title: 'Atualizações', url: '/atualizacoes', icon: BellRing },
  // { title: 'Configurações', url: '/configuracoes', icon: Settings },
];

const menuItemImportacaoXml = { title: 'Importação XML', url: '/importacao-xml', icon: FileUp };
const menuItemImportacaoSped = { title: 'Importações SPED', url: '/importacao-sped', icon: FileDigit };
const menuItemAnaliseFiscal = { title: 'Análise de Compras', url: '/analise-compras', icon: FileSearch };
const menuItemRelatoriosIA = { title: 'Relatórios com IA', url: '/relatorios-ia', icon: Sparkles };

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === 'collapsed';
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const menuItems = user?.tem_sped
    ? [...menuItemsBase, menuItemAnaliseFiscal, menuItemRelatoriosIA, menuItemImportacaoSped]
    : [...menuItemsBase, menuItemAnaliseFiscal, menuItemRelatoriosIA, menuItemImportacaoXml];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Sidebar
      variant="sidebar"
      collapsible="icon"
      className="
        shrink-0
        w-56
        group-data-[collapsible=icon]:w-14
        bg-[#0E1525]
        text-white
        border-r
        border-white/10
      "
    >
      <SidebarHeader className="gap-3 p-3 group-data-[collapsible=icon]:p-2 bg-[#0E1525]">
        <div className="flex items-center justify-between gap-2">
          <div
            className="
              flex min-w-0 items-center rounded-md bg-[#0E1525] text-white text-sm font-semibold
              border border-white/10 overflow-hidden
              px-2.5 py-1.5 w-full
              group-data-[collapsible=icon]:w-9 group-data-[collapsible=icon]:h-9
              group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:py-0
              group-data-[collapsible=icon]:justify-center
            "
            title={user?.name ?? 'Empresa'}
          >
            <span className="block w-full truncate whitespace-nowrap text-xs group-data-[collapsible=icon]:hidden">
              {user?.name ?? 'Empresa'}
            </span>

            <span className="hidden text-xs group-data-[collapsible=icon]:block">
              {(user?.name ?? 'E').slice(0, 1).toUpperCase()}
            </span>
          </div>

          <SidebarTrigger className="shrink-0 text-white hover:bg-white/10 hover:text-white" />
        </div>
      </SidebarHeader>

      <SidebarContent className="bg-[#0E1525]">
        <SidebarGroup className="px-2.5 group-data-[collapsible=icon]:px-1.5">
          <SidebarGroupContent className="flex justify-center">
            <SidebarMenu className="w-full">
              {menuItems.map((item) => {
                const isActive = location.pathname === item.url;

                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      size="sm"
                      className="h-7 text-[10px]"
                      isActive={isActive}
                      tooltip={collapsed ? item.title : undefined}
                    >
                      <NavLink
                        to={item.url}
                        className="flex items-center justify-between gap-1.5 text-[10px] text-white/80 hover:text-white group-data-[collapsible=icon]:justify-center"
                        activeClassName="bg-white/10 text-white"
                      >
                        <span className="flex items-center gap-1.5">
                          <item.icon className="h-3 w-3" />
                          <span className="group-data-[collapsible=icon]:hidden">
                            {item.title}
                          </span>
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

      <SidebarFooter className="bg-[#0E1525] p-3 group-data-[collapsible=icon]:p-2">
        <Button
          variant="outline"
          onClick={handleLogout}
          className="w-full border-white/20 text-white hover:bg-white/10 group-data-[collapsible=icon]:w-9 group-data-[collapsible=icon]:px-0"
          title="Sair"
        >
          <LogOut className="h-4 w-4" />
          <span className="group-data-[collapsible=icon]:hidden">Sair</span>
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}