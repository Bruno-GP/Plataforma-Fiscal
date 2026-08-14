import type { CSSProperties, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, Navigate, useLocation } from 'react-router-dom';

import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';
import { consultarPendenciasXmlImportados } from '@/services/nfe';
import { isContaAzulDashboardOnly, isXmlOnboardingLocked } from '@/utils/workspaceAccess';

import { AppHeader } from './AppHeader';
import { AppSidebar } from './AppSidebar';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { isAuthenticated, isReady, user } = useAuth();
  const location = useLocation();
  const xmlOnboardingLocked = isXmlOnboardingLocked(user);
  const pendenciasQuery = useQuery({
    queryKey: ['layout-pendencias-xml', user?.emitente_cnpj],
    queryFn: () => consultarPendenciasXmlImportados(user?.emitente_cnpj ?? ''),
    enabled: isAuthenticated && Boolean(user?.emitente_cnpj) && !user?.tem_sped && !user?.tem_conta_azul,
    staleTime: 5 * 60 * 1000,
  });

  const totalPendentes = pendenciasQuery.data?.total_pendentes ?? 0;

  if (!isReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (xmlOnboardingLocked && location.pathname !== '/importacao-xml') {
    return <Navigate to="/importacao-xml" replace />;
  }

  if (isContaAzulDashboardOnly(user) && location.pathname !== '/dashboard') {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <SidebarProvider style={{ '--sidebar-width-icon': '4.5rem' } as CSSProperties}>
      <div className="flex min-h-screen w-full">
        <AppSidebar />

        {/*
          A div "gap" interna do ui/sidebar.tsx (que reserva espaco no fluxo pro
          conteudo principal) usa a mesma sintaxe v3 quebrada em v4 e sempre mede
          0px, entao o main nunca era empurrado pra direita do sidebar fixo. Aqui
          sincronizamos a margem do conteudo com o mesmo estado (`peer-data-[state]`,
          exposto pelo proprio Sidebar via classe `peer`) em vez de depender dela.
        */}
        <SidebarInset className="min-w-0 flex-1 transition-[margin-left] duration-200 ease-linear md:ml-(--sidebar-width) md:peer-data-[state=collapsed]:ml-(--sidebar-width-icon)">
          <div className="min-h-screen w-full bg-[#08111f]">
            <AppHeader />
            {totalPendentes > 0 && !user?.tem_sped && !user?.tem_conta_azul && (
              <div className="border-b border-amber-400/30 bg-amber-400/10">
                <div className="mx-auto flex min-h-11 max-w-[1440px] items-center gap-2 px-4 py-2 text-sm text-amber-100 md:px-8 xl:px-10">
                  <span>
                    Ainda faltam XMLs a serem processados ({totalPendentes}). O processamento pode entrar em fila e
                    continuar em andamento; acompanhe pela tela de importacao ou pela central.
                  </span>
                  <Link to="/inconsistencias" className="ml-auto whitespace-nowrap font-semibold text-amber-200 underline">
                    Abrir central
                  </Link>
                </div>
              </div>
            )}

            <main className="min-w-0 overflow-x-hidden">
              <div className="mx-auto min-w-0 max-w-[1440px] px-4 md:px-8 xl:px-10">
                {children}
              </div>
            </main>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
