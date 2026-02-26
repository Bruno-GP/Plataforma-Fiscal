import { useEffect, useState, type ReactNode } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '@/contexts/AuthContext';
import { consultarPendenciasXmlImportados } from '@/services/nfe';

import { AppHeader } from './AppHeader';
// import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
// import { AppSidebar } from './AppSidebar';
// import { ChatWidget } from '@/components/chat/ChatWidget';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();
  const [totalPendentes, setTotalPendentes] = useState(0);

  useEffect(() => {
    const carregarPendencias = async () => {
      if (!user?.emitente_cnpj) {
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
  }, [location.pathname, user?.emitente_cnpj]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen w-full bg-background">
      <AppHeader />

      {totalPendentes > 0 && (
        <div className="border-b border-amber-200 bg-amber-50">
          <div className="mx-auto flex min-h-11 max-w-[1700px] items-center gap-2 px-4 py-2 text-sm text-amber-900 md:px-8">
            <span>
              Ainda faltam XMLs a serem processados ({totalPendentes}). O botão <strong>Processar NFe</strong> continua habilitado.
            </span>
            <Link to="/importacao-xml" className="ml-auto whitespace-nowrap font-medium underline">
              Ir para Importação XML
            </Link>
          </div>
        </div>
      )}

      <main className="min-w-0 overflow-x-hidden">
        <div className="mx-auto min-w-0 max-w-[1700px] px-4 md:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}