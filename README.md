# Python-API-XML-NFE

# Comandos para executar a API 
python -m uvicorn app.main:app --reload (Local)
ngrok http 8000 (Produção)

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

# Code API 

# API/api/Routes 

Aonde está todas as rotas para acessar o projeto 

# API/core 

Aonde está a configuração da empresa, com informações como CNPJ e razão social 

# API/domain 

Aonde fica localizado todo o funcionmanto do projeto 

# API/models

Aonde fica localizado todos os schemas referente ao XMLS 

# API/services 

Aonde fica todo o processamento para a execução da API 