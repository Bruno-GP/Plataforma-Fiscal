import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import { ChatProvider } from "@/contexts/ChatContext";

import { MainLayout } from "@/components/layout/MainLayout";

import Login from "./pages/Login";
import Dashboard from "./pages/AnaliseVendas";
import Clientes from "./pages/Clientes";
import NotFound from "./pages/NotFound";
import CadastroEmpresa from "./pages/CadastroEmpresa";
import Configuracoes from "./pages/Configuracoes";
import DetalhamentoCompras from "./pages/DetalhamentoCompras";
import DetalhamentoVendas from "./pages/DetalhamentoVendas";
import ImportacaoXML from "./pages/ImportacaoXML";
import ImportacaoSPED from "./pages/ImportacaoSPED";
import AnaliseCompras from "./pages/AnaliseCompras";
import AnaliseFiscalCfop from "./pages/AnaliseFiscalCfop";
import Inconsistencias from "./pages/Inconsistencias";
import RelatoriosIA from "./pages/RelatoriosIA";
import ReformaTributaria from "./pages/ReformaTributaria";

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

const AnaliseComprasRoute = () => <AnaliseCompras />;

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
              <Route
                path="/configuracoes"
                element={
                  <MainLayout>
                    <Configuracoes />
                  </MainLayout>
                }
              />
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
                path="/analise-compras"
                element={
                  <MainLayout>
                    <AnaliseComprasRoute />
                  </MainLayout>
                }
              />
              <Route
                path="/analise-fiscal-cfop"
                element={
                  <MainLayout>
                    <AnaliseFiscalCfop />
                  </MainLayout>
                }
              />
              <Route
                path="/reforma-tributaria"
                element={
                  <MainLayout>
                    <ReformaTributaria />
                  </MainLayout>
                }
              />
              <Route
                path="/detalhamento-vendas"
                element={
                  <MainLayout>
                    <DetalhamentoVendas />
                  </MainLayout>
                }
              />
              <Route
                path="/detalhamento-compras"
                element={
                  <MainLayout>
                    <DetalhamentoCompras />
                  </MainLayout>
                }
              />
              <Route
                path="/relatorios-ia"
                element={
                  <MainLayout>
                    <RelatoriosIA />
                  </MainLayout>
                }
              />
              <Route
                path="/inconsistencias"
                element={
                  <MainLayout>
                    <Inconsistencias />
                  </MainLayout>
                }
              />
              <Route
                path="/analise-clientes"
                element={
                  <MainLayout>
                    <Clientes />
                  </MainLayout>
                }
              />
              <Route path="/clientes" element={<Navigate to="/analise-clientes" replace />} />
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
