import {
  AlertTriangle,
  BarChart3,
  FileDigit,
  FileUp,
  Headphones,
  LogOut,
  ReceiptText,
  Scale,
  Settings,
  ShoppingCart,
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
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

const mainItems = [
  { title: 'Vendas', url: '/analise-vendas', icon: ReceiptText },
  { title: 'Compras', url: '/analise-compras', icon: ShoppingCart },
  { title: 'Clientes', url: '/analise-clientes', icon: Users },
  { title: 'Analise Fiscal', url: '/analise-fiscal-cfop', icon: BarChart3 },
];

const operationItems = [
  { title: 'Detalhar Vendas', url: '/detalhamento-vendas', icon: ReceiptText },
  { title: 'Detalhar Compras', url: '/detalhamento-compras', icon: ShoppingCart },
  { title: 'Central', url: '/inconsistencias', icon: AlertTriangle },
  { title: 'Reforma', url: '/reforma-tributaria', icon: Scale },
  { title: 'Relatorios IA', url: '/relatorios-ia', icon: Sparkles },
];

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const importacaoItem = user?.tem_sped
    ? { title: 'Importar SPED', url: '/importacao-sped', icon: FileDigit }
    : { title: 'Importar XML', url: '/importacao-xml', icon: FileUp };
  const companyName = user?.name?.trim() || 'Accounting Corp';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const renderItem = (item: (typeof mainItems)[number], compact = false) => {
    const isActive = location.pathname === item.url;

    return (
      <SidebarMenuItem key={item.url}>
        <SidebarMenuButton
          asChild
          isActive={isActive}
          className={cn(
            'h-11 rounded-md px-3 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-800/90 hover:text-slate-50 data-[active=true]:bg-emerald-500 data-[active=true]:text-slate-950',
            compact && 'h-9 text-xs font-medium',
          )}
        >
          <NavLink to={item.url} className="flex items-center gap-3">
            <item.icon className="h-4 w-4" />
            <span>{item.title}</span>
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
      <SidebarHeader className="border-b border-slate-700/70 bg-[#111827] p-5">
        <div className="space-y-6">
          <div className="text-xl font-bold text-sky-300">TaxVision Pro</div>

          <div className="space-y-1">
            <p className="truncate text-2xl font-semibold tracking-tight text-slate-100" title={companyName}>
              {companyName}
            </p>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Tax Specialist</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="bg-[#111827] px-3 py-5">
        <div className="space-y-6">
          <SidebarMenu className="gap-2">
            {mainItems.map((item) => renderItem(item))}
          </SidebarMenu>

          <div className="space-y-2">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Operacoes</p>
            <SidebarMenu className="gap-1">
              {renderItem(importacaoItem, true)}
              {operationItems.map((item) => renderItem(item, true))}
              {renderItem({ title: 'Configuracoes', url: '/configuracoes', icon: Settings }, true)}
            </SidebarMenu>
          </div>
        </div>
      </SidebarContent>

      <SidebarFooter className="mt-auto border-t border-slate-700/70 bg-[#111827] p-4">
        <div className="space-y-2">
          <Button variant="ghost" className="w-full justify-start text-slate-300">
            <Headphones className="h-4 w-4" />
            Suporte
          </Button>
          <Button variant="ghost" onClick={handleLogout} className="w-full justify-start text-rose-300 hover:text-rose-200">
            <LogOut className="h-4 w-4" />
            Sair
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
