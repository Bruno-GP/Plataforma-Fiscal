# Testes do Frontend

Este frontend usa React 18, Vite 5, TypeScript e alias `@` apontando para `src`.
A base de testes foi pensada para crescer por camadas: unitarios e integracao com Vitest, fluxos reais com Playwright, mocks HTTP com MSW e validacoes iniciais de acessibilidade/performance.

## Instalar dependencias

Use npm, pois o projeto possui `package-lock.json` atualizado:

```bash
npm install
```

## Testes unitarios e de integracao

```bash
npm run test
npm run test:run
npm run test:coverage
npm run test:ui
```

O Vitest usa `jsdom`, `@testing-library/react`, `@testing-library/user-event` e os matchers de `@testing-library/jest-dom`.
O setup global fica em `src/test/setup.ts`.

## Mocks HTTP

Os mocks ficam em:

- `src/test/mocks/handlers.ts`
- `src/test/mocks/server.ts`

Handlers globais cobrem apenas endpoints reais ja usados no codigo, como autenticacao e pendencias XML. Em testes especificos, use `server.use(...)` para sobrescrever o comportamento sem alterar o mock global.

## Helpers de renderizacao

Use `renderWithProviders` de `src/test/utils/render.tsx` para renderizar componentes com `QueryClientProvider`, `TooltipProvider` e `MemoryRouter`.

Exemplo:

```tsx
renderWithProviders(<MeuComponente />, { route: "/login" });
```

## Padroes recomendados

- Prefira `getByRole`, `getByLabelText`, `getByText` e `getByPlaceholderText`.
- Teste comportamento visivel ao usuario, nao detalhes internos.
- Evite snapshots grandes.
- Use `userEvent` para interacoes.
- Mocke apenas chamadas HTTP necessarias para o teste.

## Testes E2E

```bash
npm run e2e
npm run e2e:ui
```

O Playwright sobe o Vite automaticamente em `127.0.0.1:4173`, a menos que `PLAYWRIGHT_BASE_URL` esteja definido.

Para validar login real sem credenciais hardcoded:

```bash
E2E_LOGIN_EMAIL="usuario@empresa.com" E2E_LOGIN_PASSWORD="senha" npm run e2e
```

No Windows PowerShell:

```powershell
$env:E2E_LOGIN_EMAIL="usuario@empresa.com"
$env:E2E_LOGIN_PASSWORD="senha"
npm run e2e
```

## Acessibilidade

O smoke E2E inclui uma validacao inicial com `@axe-core/playwright` na tela de login.
Novos fluxos criticos devem incluir pelo menos uma checagem axe na pagina principal do fluxo.

## Performance

Foi adicionada uma configuracao inicial de Lighthouse CI em `lighthouserc.cjs`.
Depois de gerar o build, rode:

```bash
npm run build
npm run perf:lhci
```

As notas iniciais sao `warn` para facilitar adoção incremental.
