import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
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
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
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
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

const navGroupsBase = [
  {
    title: 'Análises',
    icon: LayoutDashboard,
    items: [
      { title: 'Análise de Vendas', url: '/analise-vendas', icon: LayoutDashboard },
      { title: 'Detalhamento de Vendas', url: '/detalhamento-vendas', icon: ListTree },
      { title: 'Análise de Compras', url: '/analise-compras', icon: FileSearch },
      { title: 'Análise de Clientes', url: '/analise-clientes', icon: Users },
    ],
  },
  {
    title: 'Fiscal',
    icon: BarChart3,
    items: [
      { title: 'Análise Fiscal', url: '/analise-fiscal-cfop', icon: BarChart3 },
      { title: 'Inconsistências Fiscais', url: '/inconsistencias', icon: AlertTriangle },
      { title: 'Reforma Tributária', url: '/reforma-tributaria', icon: Scale },
    ],
  },
];

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const importacaoItem = user?.tem_sped
    ? { title: 'Importar SPED Fiscal', url: '/importacao-sped', icon: FileDigit }
    : { title: 'Importar XML', url: '/importacao-xml', icon: FileUp };
  const navGroups = [
    ...navGroupsBase,
    {
      title: 'Importações',
      icon: FileUp,
      items: [importacaoItem],
    },
    {
      title: 'Relatórios',
      icon: Sparkles,
      items: [{ title: 'Relatórios com IA', url: '/relatorios-ia', icon: Sparkles }],
    },
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
        w-60
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
            <SidebarMenu className="w-full gap-1.5">
              {navGroups.map((group) => {
                const isActiveGroup = group.items.some((item) => location.pathname === item.url);

                return (
                  <Collapsible key={group.title} defaultOpen={isActiveGroup} className="group/collapsible">
                    <SidebarMenuItem>
                      <CollapsibleTrigger asChild>
                        <SidebarMenuButton
                          size="sm"
                          className={cn(
                            'h-9 text-sm text-white/80 hover:bg-white/10 hover:text-white',
                            isActiveGroup && 'bg-white/10 text-white',
                          )}
                        >
                          <group.icon className="h-4 w-4" />
                          <span>{group.title}</span>
                          <ChevronDown className="ml-auto h-4 w-4 transition-transform group-data-[state=open]/collapsible:rotate-180" />
                        </SidebarMenuButton>
                      </CollapsibleTrigger>

                      <CollapsibleContent>
                        <SidebarMenuSub className="mx-3 border-white/10 px-2 py-1">
                          {group.items.map((item) => {
                            const isActive = location.pathname === item.url;

                            return (
                              <SidebarMenuSubItem key={item.url}>
                                <SidebarMenuSubButton
                                  asChild
                                  size="md"
                                  isActive={isActive}
                                  className="h-8 text-white/75 hover:bg-white/10 hover:text-white data-[active=true]:bg-white data-[active=true]:text-[#0E1525]"
                                >
                                  <NavLink
                                    to={item.url}
                                    className="flex items-center gap-2"
                                    activeClassName="bg-white text-[#0E1525]"
                                  >
                                    <item.icon className="h-4 w-4" />
                                    <span>{item.title}</span>
                                  </NavLink>
                                </SidebarMenuSubButton>
                              </SidebarMenuSubItem>
                            );
                          })}
                        </SidebarMenuSub>
                      </CollapsibleContent>
                    </SidebarMenuItem>
                  </Collapsible>
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
