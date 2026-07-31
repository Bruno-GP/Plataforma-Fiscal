# Padrões de Refatoração — TypeScript / JavaScript

## Extração de Funções

**Problema:** função longa com múltiplos níveis de abstração.

```typescript
// Antes
async function handleCheckout(cartId: string) {
  const cart = await db.cart.findById(cartId);
  if (!cart || cart.items.length === 0) throw new Error("Carrinho inválido");
  let total = 0;
  for (const item of cart.items) {
    total += item.price * item.quantity;
  }
  if (total > 500) total *= 0.9;
  const order = await db.order.create({ cartId, total });
  await emailService.send(cart.userId, `Pedido #${order.id} confirmado`);
  return order;
}

// Depois
function validateCart(cart: Cart | null): asserts cart is Cart {
  if (!cart || cart.items.length === 0) throw new Error("Carrinho inválido");
}

function calculateTotal(items: CartItem[]): number {
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  return subtotal > 500 ? subtotal * 0.9 : subtotal;
}

async function handleCheckout(cartId: string): Promise<Order> {
  const cart = await db.cart.findById(cartId);
  validateCart(cart);
  const total = calculateTotal(cart.items);
  const order = await db.order.create({ cartId, total });
  await emailService.send(cart.userId, `Pedido #${order.id} confirmado`);
  return order;
}
```

---

## Separação de Responsabilidades

**Padrão para arquivos de rota/controller grandes:**

```
routes/orders.ts          → só define rotas e chama controllers
controllers/orders.ts     → orquestra: valida entrada, chama service, retorna resposta
services/orders.ts        → lógica de negócio pura (sem req/res)
repositories/orders.ts    → acesso ao banco (queries)
```

Cada camada só conhece a camada imediatamente abaixo dela.

---

## Eliminação de Código Duplicado

```typescript
// Antes
function formatUserName(user: User) {
  return `${user.firstName} ${user.lastName}`.trim();
}
function formatAdminName(admin: Admin) {
  return `${admin.firstName} ${admin.lastName}`.trim();
}

// Depois — tipo genérico com interface mínima
interface HasName {
  firstName: string;
  lastName: string;
}
function formatFullName(entity: HasName): string {
  return `${entity.firstName} ${entity.lastName}`.trim();
}
```

---

## Redução de Aninhamento — Early Return

```typescript
// Antes
async function getDiscount(userId: string) {
  const user = await db.user.findById(userId);
  if (user) {
    if (user.isActive) {
      if (user.plan === "premium") {
        return 0.2;
      } else {
        return 0.05;
      }
    } else {
      return 0;
    }
  } else {
    return 0;
  }
}

// Depois
async function getDiscount(userId: string): Promise<number> {
  const user = await db.user.findById(userId);
  if (!user || !user.isActive) return 0;
  return user.plan === "premium" ? 0.2 : 0.05;
}
```

---

## Constantes

```typescript
// Antes
if (total > 500) discount = total * 0.1;

// Depois — no topo do arquivo ou em constants.ts
const DISCOUNT_THRESHOLD = 500;
const DISCOUNT_RATE = 0.1;

if (total > DISCOUNT_THRESHOLD) discount = total * DISCOUNT_RATE;
```

---

## Tipagem

Priorizar tipagem explícita em:
- Parâmetros de função
- Retornos de função async
- Objetos de configuração
- Respostas de API

```typescript
// Ruim
async function createOrder(data: any) { ... }

// Bom
interface CreateOrderInput {
  userId: string;
  items: Array<{ productId: string; quantity: number }>;
}
async function createOrder(data: CreateOrderInput): Promise<Order> { ... }
```

Evitar `any` — usar `unknown` quando o tipo não é conhecido e fazer narrowing.

---

## Ordem de Declaração em um Módulo TypeScript

```
1. Imports (externos → internos → tipos)
2. Constantes / configuração
3. Interfaces / Types
4. Classes (se houver)
5. Funções exportadas (interface pública)
6. Funções privadas (não exportadas)
```

---

## Async/Await — Erros Comuns na Refatoração

- **Não quebrar cadeia de await**: ao extrair função assíncrona, garantir que o caller faz `await`
- **Não converter Promise para sync acidentalmente**: funções extraídas de contexto async devem continuar retornando `Promise<T>`
- **Paralelizar quando possível**: se duas operações não dependem uma da outra, usar `Promise.all`

```typescript
// Sequencial desnecessário
const user = await getUser(id);
const config = await getConfig();  // não depende de user

// Correto
const [user, config] = await Promise.all([getUser(id), getConfig()]);
```