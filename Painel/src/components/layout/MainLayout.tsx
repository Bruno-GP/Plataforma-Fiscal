import { useEffect, useState, type ReactNode } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';

import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { useAuth } from '@/contexts/AuthContext';
import { consultarPendenciasXmlImportados } from '@/services/nfe';

import { AppHeader } from './AppHeader';
import { AppSidebar } from './AppSidebar';
// import { ChatWidget } from '@/components/chat/ChatWidget';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { isAuthenticated, isReady, user } = useAuth();
  const location = useLocation();
  const [totalPendentes, setTotalPendentes] = useState(0);

  useEffect(() => {
    const carregarPendencias = async () => {
      if (!user?.emitente_cnpj || user.tem_sped) {
        setTotalPendentes(0);
        return;
      }

      try {
        const response = await consultarPendenciasXmlImportados(user.emitente_cnpj);
        setTotalPendentes(response.total_pendentes);
      } catch {
        setTotalPendentes(0);
      }
    };

    void carregarPendencias();
  }, [location.pathname, user?.emitente_cnpj, user?.tem_sped]);

  if (!isReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />

        <SidebarInset className="min-w-0 flex-1">
          <div className="min-h-screen w-full bg-[#08111f]">
            <AppHeader />
            {totalPendentes > 0 && !user?.tem_sped && (
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
