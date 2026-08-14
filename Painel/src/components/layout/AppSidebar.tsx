import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BarChart3,
  FileDigit,
  FileText,
  FileUp,
  LogOut,
  Menu,
  ReceiptText,
  Settings,
  ShoppingCart,
  Sparkles,
  Target,
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
  SidebarSeparator,
  useSidebar,
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { isContaAzulDashboardOnly, isXmlOnboardingLocked } from '@/utils/workspaceAccess';
import type { SessionUser } from '@/services/api';

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

const createNavigationGroups = (user?: Pick<SessionUser, 'tem_sped' | 'tem_conta_azul'> | null): NavigationGroup[] => {
  const importItem: NavigationItem = user?.tem_conta_azul
    ? { label: 'Conta Azul', path: '/configuracoes', icon: FileUp }
    : user?.tem_sped
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
        // { label: 'Reforma Tributaria', path: '/reforma-tributaria', icon: Scale },
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
        { label: 'Metas', path: '/metas', icon: Target },
        { label: 'Relatorios IA', path: '/relatorios-ia', icon: Sparkles },
      ],
    },
    {
      label: 'Configuracoes',
      items: [
        { label: 'Configuracoes', path: '/configuracoes', icon: Settings },
      ],
    },
  ];
};

const createLockedNavigationGroups = (): NavigationGroup[] => [
  {
    label: 'Importacoes',
    items: [{ label: 'Importar XML', path: '/importacao-xml', icon: FileUp }],
  },
];

const createContaAzulNavigationGroups = (): NavigationGroup[] => [
  {
    label: 'Visao Geral',
    items: [
      { label: 'Dashboard', path: '/dashboard', icon: BarChart3, activePaths: ['/analise-vendas'] },
    ],
  },
];

const isItemActive = (pathname: string, item: NavigationItem) =>
  pathname === item.path || item.activePaths?.some((activePath) => pathname === activePath);

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isMobile, setOpenMobile, state, toggleSidebar } = useSidebar();
  const { user, logout } = useAuth();
  const companyName = user?.name?.trim() || 'Accounting Corp';
  const xmlOnboardingLocked = isXmlOnboardingLocked(user);
  const contaAzulDashboardOnly = isContaAzulDashboardOnly(user);
  const navigationGroups = contaAzulDashboardOnly
    ? createContaAzulNavigationGroups()
    : xmlOnboardingLocked
      ? createLockedNavigationGroups()
      : createNavigationGroups(user);

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
      <SidebarMenuItem
        key={item.path}
        className="group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:justify-center"
      >
        <SidebarMenuButton
          asChild
          isActive={isActive}
          tooltip={item.label}
          className={cn(
            'h-10 rounded-md px-3 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-800/90 hover:text-slate-50',
            'data-[active=true]:bg-emerald-400/95 data-[active=true]:text-slate-950 data-[active=true]:shadow-[0_10px_28px_-18px_rgba(52,211,153,0.9)]',
            'group-data-[collapsible=icon]:mx-auto',
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
      collapsible="icon"
      // ui/sidebar.tsx usa a sintaxe antiga do Tailwind v3 (`w-[--var]`) pra largura,
      // que no v4 instalado neste projeto vira CSS invalido (colchete = valor bruto,
      // parenteses = referencia de custom property). Sobrescrevemos aqui com a
      // sintaxe v4 correta pra largura realmente mudar entre expandido/colapsado.
      className="w-(--sidebar-width) border-slate-700/70 bg-[#111827] text-slate-100 group-data-[collapsible=icon]:w-(--sidebar-width-icon)"
    >
      <SidebarHeader className="h-16 justify-center border-b border-slate-700/70 bg-[#111827] px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            aria-label={state === 'collapsed' ? 'Expandir menu' : 'Recolher menu'}
            title={state === 'collapsed' ? 'Expandir menu' : 'Recolher menu'}
            className="hidden h-8 w-8 shrink-0 text-slate-300 hover:bg-slate-800 hover:text-slate-50 md:inline-flex"
          >
            <Menu className="h-4 w-4" />
          </Button>
          <p
            className="line-clamp-2 min-w-0 flex-1 break-words text-base font-semibold leading-tight tracking-tight text-slate-100 group-data-[collapsible=icon]:hidden"
            title={companyName}
          >
            {companyName}
          </p>
        </div>
      </SidebarHeader>

      <SidebarContent className="taxvision-sidebar-scroll bg-[#111827] px-3 py-4">
        <div className="space-y-3">
          {navigationGroups.map((group, index) => {
            const isGroupActive = group.items.some((item) => isItemActive(location.pathname, item));

            return (
              <div key={group.label}>
                {index > 0 && (
                  <SidebarSeparator className="mb-3 hidden bg-slate-700/60 group-data-[collapsible=icon]:block" />
                )}
                <SidebarGroup
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
                    <SidebarMenu className="gap-1 group-data-[collapsible=icon]:gap-2">
                      {group.items.map((item) => renderItem(item))}
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              </div>
            );
          })}
        </div>
      </SidebarContent>

      <SidebarFooter className="mt-auto border-t border-slate-700/70 bg-[#111827] p-4 group-data-[collapsible=icon]:px-2">
        <div className="space-y-2">
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
