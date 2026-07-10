# Frontend — Arquitetura e Padrões

Este documento cobre a estrutura interna do Painel, os padrões adotados e como adicionar novas páginas. Para setup e rotas ativas consulte `Painel/README.md`; para contratos de API consulte `docs/api-contracts.md`.

## Arquivos de referência no código

- `Painel/src/App.tsx`
- `Painel/src/components/layout/MainLayout.tsx`
- `Painel/src/components/layout/AppSidebar.tsx`
- `Painel/src/contexts/AuthContext.tsx`
- `Painel/src/services/api.ts`
- `Painel/src/services/fiscalSource.ts`
- `Painel/src/services/operations.ts`
- `Painel/src/services/jobs.ts`
- `Painel/src/hooks/useProcessingJobFlow.ts`
- `Painel/src/hooks/usePeriodFilter.ts`
- `Painel/src/hooks/useFiscalYears.ts`
- `Painel/src/hooks/useImportFileQueue.ts`
- `Painel/src/hooks/useDashboardQueries.ts`
- `Painel/src/utils/workspaceAccess.ts`

## Estrutura de pastas

```text
Painel/src/
|-- App.tsx                  # Roteador principal e providers globais
|-- main.tsx                 # Entry point
|-- components/
|   |-- layout/              # MainLayout, AppSidebar, AppHeader
|   |-- ui/                  # Componentes Radix UI / shadcn (não editar diretamente)
|   |-- NavLink.tsx
|   `-- reports/             # Componentes de relatórios IA
|-- contexts/
|   |-- AuthContext.tsx      # Sessão, login, logout, register
|   `-- ChatContext.tsx      # Chat (desabilitado)
|-- features/                # Lógica e componentes por domínio
|   |-- importacaoXML/
|   |-- importacaoSPED/
|   |-- analiseVendas/
|   |-- analiseCompras/
|   |-- clientes/
|   |-- detalhamentoVendas/
|   |-- detalhamentoCompras/
|   |-- inconsistencias/
|   |-- reformaTributaria/
|   |-- relatoriosIA/
|   |-- configuracoes/
|   `-- cadastroEmpresa/
|-- hooks/                   # Hooks reutilizáveis entre features
|-- pages/                   # Entry points de rota (finos — delegam para features/)
|-- services/                # Chamadas HTTP e utilitários de estado persistido
|-- utils/                   # Helpers puros
`-- lib/                     # Utilitários de biblioteca (cn, etc.)
```

## Padrão de feature

Cada feature segue esta estrutura interna:

```text
features/nomeDaFeature/
|-- components/      # Componentes React exclusivos da feature
|-- helpers/         # Funções puras de transformação/formatação
|-- hooks/           # Hook principal de dados da página (useNomeDaFeaturePageData)
`-- types.ts         # Tipos e interfaces da feature
```

A página em `pages/` consome apenas o hook de dados da feature e monta os componentes:

```tsx
// pages/ImportacaoXML.tsx
export default function ImportacaoXML() {
  const data = useImportacaoXmlPageData();
  return (
    <>
      <ImportacaoXmlFileSelection {...data} />
      <ImportacaoXmlActions {...data} />
      <ImportacaoXmlResultsPanel {...data} />
    </>
  );
}
```

O hook de dados retorna um objeto tipado pela interface `NomeDaFeaturePageData` definida em `types.ts`. A página não contém lógica — ela apenas distribui props.

## Camadas de chamada HTTP

```
páginas/features
    ↓
services/ (nfe.ts, sped.ts, jobs.ts, etc.)
    ↓
services/api.ts (apiFetch — injeta auth header e trata 401)
    ↓
API backend
```

`apiFetch` (`services/api.ts`) é o único ponto de saída HTTP. Ele:
- Injeta `Authorization: Bearer <token>` quando há `accessToken` na sessão.
- Envia `credentials: 'include'` para o cookie HttpOnly funcionar em cross-origin.
- Remove a sessão do localStorage quando recebe `401`.

Não use `fetch` diretamente nas features. Sempre passe por `apiFetch` ou pelos helpers de service.

## Abstração de fonte fiscal (fiscalSource)

A plataforma tem dois perfis: empresas XML/NFe e empresas SPED. Em vez de duplicar chamadas nas páginas, `services/fiscalSource.ts` expõe uma API unificada:

```ts
const fiscalApi = createFiscalSourceApi(user?.tem_sped);

fiscalApi.dashboardCompras(params);   // chama NFe ou SPED automaticamente
fiscalApi.analiseVendas(params);
fiscalApi.kpis(params);
```

Use `createFiscalSourceApi` sempre que um dashboard ou análise servir ambos os perfis. Não duplique chamadas NFe/SPED na mesma página.

## Autenticação e sessão

`AuthContext` é o único ponto de acesso à sessão. Expõe:

| Prop/método | Uso |
|---|---|
| `user` | Objeto com `id`, `email`, `emitente_cnpj`, `tem_sped`, `tem_xml_importado_valido` |
| `isAuthenticated` | `true` quando há usuário |
| `isReady` | `true` após a hidratação inicial (verificação no servidor) |
| `login(email, senha)` | Autentica e retorna `{ ok, redirectTo?, message? }` |
| `register(...)` | Cadastra empresa e retorna `{ ok, message? }` |
| `logout()` | Limpa sessão local e chama `/api/auth/sair` |
| `refreshSession()` | Ressincroniza dados do servidor sem deslogar em falha |

### Fluxo de hidratação

Ao montar o app, `AuthContext` chama `GET /api/auth/sessao` para validar a sessão com o servidor. Enquanto `isReady` for `false`, o `MainLayout` renderiza `null` evitando flashes de tela protegida.

### localStorage

| Chave | Conteúdo | Motivo |
|---|---|---|
| `auth_session` | `{ user, expiresAt, accessToken }` | Hidratação síncrona antes da verificação no servidor |
| `user` | Objeto de usuário (legado) | Compatibilidade com código anterior a `auth_session` |
| `fiscal_operations` | Últimas 12 operações de importação/processamento | Histórico local exibido em Inconsistências |
| `dashboard_fiscal_years` | Anos disponíveis por CNPJ/fonte | Evita requisição de anos ao abrir dashboard |

Risco: dados em `localStorage` são visíveis a scripts injetados por XSS. O token sensível fica no cookie HttpOnly; o `localStorage` é conveniência de UI, não fronteira de segurança.

## Controle de acesso e onboarding lock

`utils/workspaceAccess.ts` centraliza as duas regras de acesso:

```ts
// Empresa XML sem nenhum XML válido importado
isXmlOnboardingLocked(user) // true → redireciona para /importacao-xml

// Rota padrão após login
getDefaultWorkspaceRoute(user) // '/importacao-xml' ou '/dashboard'
```

O `MainLayout` usa `isXmlOnboardingLocked` para forçar a empresa XML a importar antes de acessar qualquer outra tela. O `AppSidebar` esconde todas as entradas de menu quando o lock está ativo.

### Redirecionamento por perfil fiscal

O `App.tsx` usa `ImportacaoFiscalRoute` para redirecionar empresas para o fluxo correto:
- Empresa `tem_sped=true` acessando `/importacao-xml` → redireciona para `/importacao-sped`
- Empresa `tem_sped=false` acessando `/importacao-sped` → redireciona para `/importacao-xml`

## Hooks reutilizáveis

### `useProcessingJobFlow`

Encapsula criação, polling e cancelamento de jobs assíncronos.

```ts
const { isProcessing, currentJob, runProcessingJob, cancelProcessing } = useProcessingJobFlow();

await runProcessingJob({
  createJob: (signal) => processarXmlsImportados(cnpj, { signal }),
  onCreated: (job) => console.log(job.job_id),
  onUpdate: (job) => console.log(job.status),
});
```

- Polling a cada 2,5 s (padrão), timeout de 15 min.
- `cancelProcessing()` aborta o acompanhamento na tela; o job pode continuar no backend.
- Para acompanhar um job já criado sem criar outro: `trackCreatedJob(createdJob, options)`.

### `usePeriodFilter`

Gerencia os filtros de ano e mês de dashboards e análises.

```ts
const {
  selectedYear, setSelectedYear,
  selectedMonth, setSelectedMonth,
  year, monthNumber,
  ensureValidYear,
  faturamentoPeriodo,
} = usePeriodFilter();
```

Chame `ensureValidYear(anosDisponiveis)` após receber os anos da API para corrigir um ano selecionado que não existe nos dados.

### `useFiscalYears`

Deriva e mantém a lista de anos disponíveis a partir dos dados retornados pela API.

```ts
const { availableYears, selectedYearNumber } = useFiscalYears({
  entries: kpisData?.resultados,
  selectedYear,
  setSelectedYear,
  includeCurrentYear: true,
});
```

### `useImportFileQueue`

Gerencia a fila de arquivos selecionados antes do upload.

```ts
const { selectedFiles, addFiles, clearFiles, totalSize, formatFileSize } = useImportFileQueue({
  maxFiles: 10000,
  acceptedExtensions: ['.xml'],
  onLimitExceeded: ({ maxFiles }) => toast({ title: `Máximo: ${maxFiles}` }),
});
```

Filtra por extensão, deduplica por nome e respeita o limite de arquivos.

### `useDashboardComprasQueries` / `useDashboardVendasQueries`

Orquestram a busca de anos disponíveis e dados do dashboard com cache local em `localStorage` para evitar requisições desnecessárias ao reabrir a página.

## Histórico de operações (operations.ts)

`saveFiscalOperation` grava no `localStorage` as últimas 12 operações de importação e processamento. A página de Inconsistências lê esse histórico com `readFiscalOperations`.

```ts
saveFiscalOperation({
  type: 'xml-import',
  status: 'success',
  title: 'Importação XML concluída',
  description: 'Importados: 42. Duplicados: 3. Erros: 0.',
  cnpj: user.emitente_cnpj,
  jobId: job.job_id,
  jobStatus: job.status,
});
```

## Como adicionar uma nova página

### 1. Criar a estrutura da feature

```text
src/features/nomeDaFeature/
  components/
    NomeDaFeatureCard.tsx
  hooks/
    useNomeDaFeaturePageData.ts
  types.ts
```

### 2. Definir os tipos

Em `types.ts`, declare a interface de dados que o hook retorna e as props dos componentes:

```ts
export interface NomeDaFeaturePageData {
  isLoading: boolean;
  data: MinhaResposta | undefined;
}
```

### 3. Implementar o hook de dados

Em `hooks/useNomeDaFeaturePageData.ts`:

```ts
export function useNomeDaFeaturePageData(): NomeDaFeaturePageData {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ['nome-da-feature', user?.emitente_cnpj],
    queryFn: () => fetchMeuEndpoint(user?.emitente_cnpj ?? ''),
    enabled: Boolean(user?.emitente_cnpj),
    staleTime: 5 * 60 * 1000,
  });

  return { isLoading: query.isLoading, data: query.data };
}
```

### 4. Criar a página (entry point)

Em `src/pages/NomeDaFeature.tsx`:

```tsx
import { useNomeDaFeaturePageData } from '@/features/nomeDaFeature/hooks/useNomeDaFeaturePageData';
import { NomeDaFeatureCard } from '@/features/nomeDaFeature/components/NomeDaFeatureCard';

export default function NomeDaFeature() {
  const data = useNomeDaFeaturePageData();
  return (
    <div className="space-y-6 py-6">
      <h1 className="text-2xl font-semibold tracking-tight">Nome da Feature</h1>
      <NomeDaFeatureCard {...data} />
    </div>
  );
}
```

### 5. Registrar a rota em App.tsx

```tsx
import NomeDaFeature from './pages/NomeDaFeature';

// Dentro de <Routes>:
<Route
  path="/nome-da-feature"
  element={
    <MainLayout>
      <NomeDaFeature />
    </MainLayout>
  }
/>
```

### 6. Adicionar ao menu lateral (AppSidebar.tsx)

Em `createNavigationGroups`, adicione o item ao grupo adequado:

```ts
{ label: 'Nome da Feature', path: '/nome-da-feature', icon: IconeEscolhido }
```

## Funcionalidades desabilitadas

Estas funcionalidades têm código implementado mas estão desligadas:

| Funcionalidade | Onde está desabilitada | Como habilitar |
|---|---|---|
| Chat | `ChatWidget` comentado em `MainLayout.tsx` | Descomentar import e `<ChatWidget />` e conectar `ChatContext` à API |
| Atualizações | Rota comentada em `App.tsx` | Descomentar o `<Route path="/atualizacoes" ...>` e o import |
| Reforma Tributária no menu | Item comentado em `AppSidebar.tsx` | Descomentar `{ label: 'Reforma Tributaria', path: '/reforma-tributaria', ... }` |
| Botão Suporte | `<Button>` comentado no footer do `AppSidebar.tsx` | Descomentar e conectar ao destino de suporte |

Nota: a rota `/reforma-tributaria` está ativa em `App.tsx`; apenas o link no menu está comentado.

## Checklist para novas features

- A página delega toda a lógica para o hook de dados da feature?
- O hook usa `useQuery` com `queryKey` que inclui o CNPJ da empresa?
- Chamadas HTTP passam por `apiFetch` via service?
- Features que servem XML e SPED usam `createFiscalSourceApi` em vez de duplicar chamadas?
- O `staleTime` está configurado para evitar refetches desnecessários?
- Operações de importação/processamento chamam `saveFiscalOperation`?
- A rota está registrada em `App.tsx` dentro de `<MainLayout>`?
- O item de menu foi adicionado em `AppSidebar.tsx`?
