import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import { ChatProvider } from "@/contexts/ChatContext";

import { MainLayout } from "@/components/layout/MainLayout";

import Login from "./pages/Login";
import Dashboard from "./pages/dashboard/AnaliseVendas";
import Faturamento from "./pages/faturamento/components/Faturamento";
import Clientes from "./pages/Clientes";
import Configuracoes from "./pages/Configuracoes";
import NotFound from "./pages/NotFound";
import CadastroEmpresa from "./pages/CadastroEmpresa";
import ImportacaoXML from "./pages/ImportacaoXML";
import Atualizacoes from "./pages/Atualizacoes";
import ImportacaoSPED from "./pages/ImportacaoSPED";
import AnaliseFiscal from "./pages/AnaliseFiscal";

// QueryClient centraliza cache e invalidação de chamadas HTTP da aplicação.
const queryClient = new QueryClient();

const ImportacaoFiscalRoute = ({ tipo }: { tipo: 'xml' | 'sped' }) => {
  const { user } = useAuth();

  if (tipo === 'xml' && user?.tem_sped) {
    return <Navigate to="/importacao-sped" replace />;
  }

  if (tipo === 'sped' && !user?.tem_sped) {
    return <Navigate to="/importacao-xml" replace />;
  }

  return tipo === 'xml' ? <ImportacaoXML /> : <ImportacaoSPED />;
};

const AnaliseFiscalRoute = () => {
  const { user } = useAuth();

  if (!user?.tem_sped) {
    return <Navigate to="/analise-vendas" replace />;
  }

  return <AnaliseFiscal />;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <AuthProvider>
        <ChatProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>

            {/*
              Rotas principais da aplicação.
              Para criar uma nova página, adicione import + <Route> aqui
              e, quando necessário, encapsule com <MainLayout>.
            */}
            
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/interno/cadastro-empresa" element={<CadastroEmpresa />} />
              <Route
                path="/analise-vendas"
                element={
                  <MainLayout>
                    <Dashboard />
                  </MainLayout>
                }
              />
              <Route path="/dashboard" element={<Navigate to="/analise-vendas" replace />} />
              <Route
                path="/faturamento"
                element={
                  <MainLayout>
                    <Faturamento />
                  </MainLayout>
                }
              />
              {/* <Route
                path="/clientes"
                element={
                  <MainLayout>
                    <Clientes />
                  </MainLayout>
                }
              />
              <Route
                path="/configuracoes"
                element={
                  <MainLayout>
                    <Configuracoes />
                  </MainLayout>
                }
              /> */}
              <Route
                path="/importacao-xml"
                element={
                  <MainLayout>
                    <ImportacaoFiscalRoute tipo="xml" />
                  </MainLayout>
                }
              />
              <Route
                path="/importacao-sped"
                element={
                  <MainLayout>
                    <ImportacaoFiscalRoute tipo="sped" />
                  </MainLayout>
                }
              />
              <Route
                path="/analise-fiscal"
                element={
                  <MainLayout>
                    <AnaliseFiscalRoute />
                  </MainLayout>
                }
              />
              {/* <Route
                path="/atualizacoes"
                element={
                  <MainLayout>
                    <Atualizacoes />
                  </MainLayout>
                }
              /> */}
              <Route path="/" element={<Navigate to="/analise-vendas" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </ChatProvider>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;