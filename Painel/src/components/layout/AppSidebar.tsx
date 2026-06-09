import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BarChart3,
  FileDigit,
  FileText,
  FileUp,
  Headphones,
  LogOut,
  ReceiptText,
  Scale,
  Settings,
  ShoppingCart,
  Sparkles,
  TrendingUp,
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
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { isXmlOnboardingLocked } from '@/utils/workspaceAccess';

type NavigationItem = {
  label: string;
  path: string;
  icon: LucideIcon;
  activePaths?: string[];
};

type NavigationGroup = {
  label: string;
  items: NavigationItem[];
};

const createNavigationGroups = (temSped?: boolean): NavigationGroup[] => {
  const importItem: NavigationItem = temSped
    ? { label: 'Importar SPED', path: '/importacao-sped', icon: FileDigit }
    : { label: 'Importar XML', path: '/importacao-xml', icon: FileUp };

  return [
    {
      label: 'Visao Geral',
      items: [
        { label: 'Dashboard', path: '/dashboard', icon: BarChart3, activePaths: ['/analise-vendas'] },
      ],
    },
    {
      label: 'Fiscal',
      items: [
        { label: 'Analise Fiscal', path: '/analise-fiscal-cfop', icon: FileText },
        { label: 'Reforma Tributaria', path: '/reforma-tributaria', icon: Scale },
      ],
    },
    {
      label: 'Importacoes',
      items: [
        importItem,
        { label: 'Processamentos', path: '/inconsistencias', icon: Activity },
      ],
    },
    {
      label: 'Operacoes',
      items: [
        { label: 'Compras', path: '/analise-compras', icon: ShoppingCart },
        { label: 'Clientes', path: '/analise-clientes', icon: Users, activePaths: ['/clientes'] },
        { label: 'Detalhamento de Vendas', path: '/detalhamento-vendas', icon: TrendingUp },
        { label: 'Detalhamento de Compras', path: '/detalhamento-compras', icon: ReceiptText },
      ],
    },
    {
      label: 'Relatorios',
      items: [
        { label: 'Relatorios IA', path: '/relatorios-ia', icon: Sparkles },
      ],
    },
    // {
    //   label: 'Configuracoes',
    //   items: [
    //     { label: 'Configuracoes', path: '/configuracoes', icon: Settings },
    //   ],
    // },
  ];
};

const createLockedNavigationGroups = (): NavigationGroup[] => [
  {
    label: 'Importacoes',
    items: [{ label: 'Importar XML', path: '/importacao-xml', icon: FileUp }],
  },
];

const isItemActive = (pathname: string, item: NavigationItem) =>
  pathname === item.path || item.activePaths?.some((activePath) => pathname === activePath);

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isMobile, setOpenMobile } = useSidebar();
  const { user, logout } = useAuth();
  const companyName = user?.name?.trim() || 'Accounting Corp';
  const xmlOnboardingLocked = isXmlOnboardingLocked(user);
  const navigationGroups = xmlOnboardingLocked ? createLockedNavigationGroups() : createNavigationGroups(user?.tem_sped);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNavigation = () => {
    if (isMobile) {
      setOpenMobile(false);
    }
  };

  const renderItem = (item: NavigationItem) => {
    const isActive = isItemActive(location.pathname, item);

    return (
      <SidebarMenuItem key={item.path}>
        <SidebarMenuButton
          asChild
          isActive={isActive}
          tooltip={item.label}
          className={cn(
            'h-10 rounded-md px-3 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-800/90 hover:text-slate-50',
            'data-[active=true]:bg-emerald-400/95 data-[active=true]:text-slate-950 data-[active=true]:shadow-[0_10px_28px_-18px_rgba(52,211,153,0.9)]',
            'group-data-[collapsible=icon]:mx-auto group-data-[collapsible=icon]:h-9 group-data-[collapsible=icon]:w-9',
          )}
        >
          <NavLink to={item.path} onClick={handleNavigation} className="flex min-w-0 items-center gap-3">
            <item.icon className="h-4 w-4 shrink-0" />
            <span className="truncate group-data-[collapsible=icon]:hidden">{item.label}</span>
          </NavLink>
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  };

  return (
    <Sidebar
      variant="sidebar"
      collapsible="none"
      className="sticky top-0 h-svh w-64 shrink-0 border-r border-slate-700/70 bg-[#111827] text-slate-100"
    >
      <SidebarHeader className="h-16 justify-center border-b border-slate-700/70 bg-[#111827] px-5 py-2 group-data-[collapsible=icon]:px-2">
        <div className="min-w-0 space-y-6 group-data-[collapsible=icon]:space-y-0">
          {/* <div className="text-xl font-bold text-sky-300 group-data-[collapsible=icon]:text-center group-data-[collapsible=icon]:text-lg">
            <span className="group-data-[collapsible=icon]:hidden">TaxVision Pro</span>
            <span className="hidden group-data-[collapsible=icon]:inline">TV</span>
          </div> */}

          <div className="min-w-0 space-y-1 group-data-[collapsible=icon]:hidden">
            <p className="line-clamp-2 break-words text-base font-semibold leading-tight tracking-tight text-slate-100" title={companyName}>
              {companyName}
            </p>
            {/* <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Tax Specialist</p> */}
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="taxvision-sidebar-scroll bg-[#111827] px-3 py-4">
        <div className="space-y-3">
          {navigationGroups.map((group) => {
            const isGroupActive = group.items.some((item) => isItemActive(location.pathname, item));

            return (
              <SidebarGroup
                key={group.label}
                className={cn(
                  'rounded-lg px-0 py-1',
                  isGroupActive && 'bg-slate-900/50 ring-1 ring-slate-700/70',
                  'group-data-[collapsible=icon]:bg-transparent group-data-[collapsible=icon]:ring-0',
                )}
              >
                <SidebarGroupLabel
                  className={cn(
                    'h-7 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500',
                    isGroupActive && 'text-sky-300',
                  )}
                >
                  {group.label}
                </SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenu className="gap-1">
                    {group.items.map((item) => renderItem(item))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            );
          })}
        </div>
      </SidebarContent>

      <SidebarFooter className="mt-auto border-t border-slate-700/70 bg-[#111827] p-4 group-data-[collapsible=icon]:px-2">
        <div className="space-y-2">
          {/* <Button
            variant="ghost"
            className="w-full justify-start gap-3 text-slate-300 hover:bg-slate-800 hover:text-slate-50 group-data-[collapsible=icon]:h-9 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
          >
            <Headphones className="h-4 w-4" />
            <span className="group-data-[collapsible=icon]:hidden">Suporte</span>
          </Button> */}
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="w-full justify-start gap-3 text-rose-300 hover:bg-slate-800 hover:text-rose-200 group-data-[collapsible=icon]:h-9 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
          >
            <LogOut className="h-4 w-4" />
            <span className="group-data-[collapsible=icon]:hidden">Sair</span>
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
