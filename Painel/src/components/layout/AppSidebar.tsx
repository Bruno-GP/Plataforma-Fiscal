import { FileUp, LayoutDashboard, Receipt } from 'lucide-react';
import { useLocation } from 'react-router-dom';

import { NavLink } from '@/components/NavLink';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  useSidebar,
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';

const menuItems = [
  { title: 'Dashboard', url: '/dashboard', icon: LayoutDashboard },
  { title: 'Faturamento', url: '/faturamento', icon: Receipt },
  { title: 'Importação XML', url: '/importacao-xml', icon: FileUp },
  // { title: 'Clientes', url: '/clientes', icon: Users },
  // { title: 'Configurações', url: '/configuracoes', icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === 'collapsed';
  const location = useLocation();
  const { user } = useAuth();

  return (
    <Sidebar
      variant="sidebar"
      collapsible="icon"
      className="hidden md:flex shrink-0 bg-[#0E1525] text-white border-r border-white/10"
    >
      <SidebarHeader className="p-4 group-data-[collapsible=icon]:p-2 bg-[#0E1525]">
        <div className="flex min-w-0 items-center gap-2 group-data-[collapsible=icon]:justify-center">
          <div
            className="
              flex min-w-0 items-center rounded-md bg-[#0E1525] text-white text-sm font-semibold
              border border-white/10 overflow-hidden
              px-3 py-2 w-full
              group-data-[collapsible=icon]:w-10 group-data-[collapsible=icon]:h-10
              group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:py-0
              group-data-[collapsible=icon]:justify-center
            "
            title={user?.name ?? 'Empresa'}
          >
            <span className="block w-full truncate whitespace-nowrap group-data-[collapsible=icon]:hidden">
              {user?.name ?? 'Empresa'}
            </span>

            <span className="hidden group-data-[collapsible=icon]:block">
              {(user?.name ?? 'E').slice(0, 1).toUpperCase()}
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="bg-[#0E1525]">
        <SidebarGroup className="px-4 group-data-[collapsible=icon]:px-2">
          <SidebarGroupContent className="flex justify-center">
            <SidebarMenu className="w-full">
              {menuItems.map((item) => {
                const isActive = location.pathname === item.url;
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      size="sm"
                      isActive={isActive}
                      tooltip={collapsed ? item.title : undefined}
                    >
                      <NavLink
                        to={item.url}
                        className="flex items-center gap-2 group-data-[collapsible=icon]:justify-center text-sm text-white/80 hover:text-white"
                        activeClassName="bg-white/10 text-white"
                      >
                        <item.icon className="h-4 w-4" />
                        <span className="group-data-[collapsible=icon]:hidden">
                          {item.title}
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
    </Sidebar>
  );
}
