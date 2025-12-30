# Python-API-XML-NFE

# API de Relatórios Fiscais

## Objetivo
API responsável por gerar relatórios fiscais, analíticos e executivos
a partir de dados estruturados (XML, SPED, banco de dados).

## Fluxo no Make
HTTP → Router → Relatórios → Base Legal → Plano de Ação → HTML → Gmail

## Endpoints

### POST /relatorios
Gera relatórios fiscais consolidados.

Parâmetros:
- empresa_id (string)
- periodo (YYYY-MM)
- tipo_relatorio (executivo | analitico | fiscal)

Resposta:
- status
- resumo
- indicadores
- alertas
