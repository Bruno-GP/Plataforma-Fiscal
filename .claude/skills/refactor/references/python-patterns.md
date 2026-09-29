# Padrões de Refatoração — Python

## Extração de Funções

**Problema:** função longa com múltiplos níveis de abstração misturados.

```python
# Antes
def process_order(order_data):
    # validar
    if not order_data.get("items"):
        raise ValueError("Pedido sem itens")
    if order_data.get("total") <= 0:
        raise ValueError("Total inválido")
    # calcular desconto
    discount = 0
    if order_data["total"] > 500:
        discount = order_data["total"] * 0.1
    elif order_data["total"] > 200:
        discount = order_data["total"] * 0.05
    # salvar
    db.save({**order_data, "discount": discount})

# Depois
def _validate_order(order_data: dict) -> None:
    if not order_data.get("items"):
        raise ValueError("Pedido sem itens")
    if order_data.get("total", 0) <= 0:
        raise ValueError("Total inválido")

def _calculate_discount(total: float) -> float:
    if total > 500:
        return total * 0.1
    if total > 200:
        return total * 0.05
    return 0.0

def process_order(order_data: dict) -> None:
    _validate_order(order_data)
    discount = _calculate_discount(order_data["total"])
    db.save({**order_data, "discount": discount})
```

**Regra:** funções prefixadas com `_` são internas ao módulo. Só exportar o que é interface pública.

---

## Separação de Responsabilidades (SRP)

**Problema:** acesso a banco + lógica de negócio + formatação na mesma função.

Estratégia:
1. Identificar as responsabilidades (ex: validação, cálculo, persistência, serialização)
2. Criar uma função para cada
3. A função original vira um orquestrador que chama as outras em sequência

```python
# Padrão de orquestrador
def process_order(order_data: dict) -> dict:
    validated = validate_order(order_data)       # validação
    priced = apply_pricing_rules(validated)       # regra de negócio
    saved = save_order(priced)                    # persistência
    return format_order_response(saved)           # serialização
```

---

## Eliminação de Código Duplicado

**Problema:** blocos similares repetidos com pequenas variações.

```python
# Antes — duplicação com variação mínima
def notify_admin(message):
    payload = {"to": "admin@empresa.com", "body": message, "priority": "high"}
    requests.post(NOTIFY_URL, json=payload)

def notify_support(message):
    payload = {"to": "suporte@empresa.com", "body": message, "priority": "normal"}
    requests.post(NOTIFY_URL, json=payload)

# Depois — parametrizado
def _send_notification(to: str, message: str, priority: str = "normal") -> None:
    payload = {"to": to, "body": message, "priority": priority}
    requests.post(NOTIFY_URL, json=payload)

def notify_admin(message: str) -> None:
    _send_notification("admin@empresa.com", message, priority="high")

def notify_support(message: str) -> None:
    _send_notification("suporte@empresa.com", message)
```

---

## Redução de Aninhamento

**Técnica: Early Return (Guard Clauses)**

```python
# Antes — pyramid of doom
def get_user_discount(user_id):
    user = db.get_user(user_id)
    if user:
        if user.is_active:
            if user.subscription == "premium":
                return 0.20
            else:
                return 0.05
        else:
            return 0
    else:
        return 0

# Depois — guard clauses
def get_user_discount(user_id: int) -> float:
    user = db.get_user(user_id)
    if not user or not user.is_active:
        return 0.0
    if user.subscription == "premium":
        return 0.20
    return 0.05
```

---

## Constantes e Configuração

```python
# Antes — magic numbers espalhados
if total > 500:
    discount = total * 0.10

# Depois — constantes nomeadas no topo do arquivo ou em config
DISCOUNT_THRESHOLD_HIGH = 500
DISCOUNT_RATE_HIGH = 0.10

if total > DISCOUNT_THRESHOLD_HIGH:
    discount = total * DISCOUNT_RATE_HIGH
```

---

## Type Hints

Adicionar em funções públicas e nas que têm lógica complexa:

```python
from typing import Optional

def find_product(code: str, active_only: bool = True) -> Optional[dict]:
    ...
```

Não é necessário tipar variáveis locais simples — só parâmetros e retornos.

---

## Ordem de Declaração em um Módulo

```
1. Imports (stdlib → third-party → local)
2. Constantes / configuração
3. Classes (se houver)
4. Funções públicas
5. Funções privadas (prefixo _)
6. Bloco if __name__ == "__main__" (se aplicável)
```