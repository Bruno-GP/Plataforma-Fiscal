import {
  AlertTriangle,
  BarChart3,
  FileDigit,
  FileSearch,
  FileUp,
  LayoutDashboard,
  ListTree,
  LogOut,
  Scale,
  Sparkles,
  Users,
} from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { NavLink } from '@/components/NavLink';
import { Button } from '@/components/ui/button';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';

const menuItemsBase = [
  { title: 'Vendas', url: '/analise-vendas', icon: LayoutDashboard },
  { title: 'Detalhamento Vendas', url: '/detalhamento-vendas', icon: ListTree },
  { title: 'Análise Fiscal', url: '/analise-fiscal-cfop', icon: BarChart3 },
  { title: 'Clientes', url: '/analise-clientes', icon: Users },
];

const menuItemImportacaoXml = { title: 'Importacao XML', url: '/importacao-xml', icon: FileUp };
const menuItemImportacaoSped = { title: 'Importacoes SPED', url: '/importacao-sped', icon: FileDigit };
const menuItemAnaliseCompras = { title: 'Compras', url: '/analise-compras', icon: FileSearch };
const menuItemReformaTributaria = { title: 'Reforma Tributaria', url: '/reforma-tributaria', icon: Scale };
// const menuItemDetalhamentoCompras = { title: 'Detalhe compras', url: '/detalhamento-compras', icon: ListTree };
const menuItemRelatoriosIA = { title: 'Relatorios com IA', url: '/relatorios-ia', icon: Sparkles };
const menuItemInconsistencias = { title: 'Inconsistencias', url: '/inconsistencias', icon: AlertTriangle };

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const menuItems = user?.tem_sped
    ? [
        ...menuItemsBase,
        menuItemAnaliseCompras,
        menuItemReformaTributaria,
        // menuItemDetalhamentoCompras,
        menuItemRelatoriosIA,
        menuItemInconsistencias,
        menuItemImportacaoSped,
      ]
    : [
        ...menuItemsBase,
        menuItemAnaliseCompras,
        menuItemReformaTributaria,
        // menuItemDetalhamentoCompras,
        menuItemRelatoriosIA,
        menuItemInconsistencias,
        menuItemImportacaoXml,
      ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Sidebar
      variant="sidebar"
      collapsible="none"
      className="
        sticky top-0
        h-svh
        w-56
        shrink-0
        border-r border-white/10
        bg-[#0E1525]
        text-white
      "
    >
      <SidebarHeader className="gap-3 bg-[#0E1525] p-3">
        <div className="flex items-center justify-between gap-2">
          <div
            className="
              flex min-w-0 w-full items-center overflow-hidden rounded-md border border-white/10
              bg-[#0E1525] px-2.5 py-1.5 text-sm font-semibold text-white
            "
            title={user?.name ?? 'Empresa'}
          >
            <span className="block w-full truncate whitespace-nowrap text-xs">
              {user?.name ?? 'Empresa'}
            </span>
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
        <Button variant="outline" onClick={handleLogout} title="Sair">
          <LogOut className="h-4 w-4" />
          <span>Sair</span>
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
