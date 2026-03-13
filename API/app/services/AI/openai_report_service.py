import logging
import os
from decimal import Decimal
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger("OpenAIReportService")

class OpenAIReportService:
  def __init__(self):
    self.api_key = os.getenv("OPENAI_API_KEY")
    self.model = os.getenv("OPENAI_REPORT_MODEL", "gpt-4o-mini")
    self.system_prompt = self._carregar_prompt_agente()

  def disponivel(self) -> bool:
    return bool(self.api_key)

  def gerar_relatorio_compras(self, analise: dict) -> str:
    if not self.api_key:
      raise ValueError("OPENAI_API_KEY não configurada.")

    cliente = OpenAI(api_key=self.api_key)

    prompt = self._montar_prompt_compras(analise)

    resposta = cliente.responses.create(
      model=self.model,
      input=[
        {
          "role": "system",
          "content": self.system_prompt,
        },
        {"role": "user", "content": prompt},
      ],
      temperature=0.3,
      max_output_tokens=500,
    )

    texto = (resposta.output_text or "").strip()
    if not texto:
      logger.warning("OpenAI não retornou conteúdo textual no relatório.")
      return "Não foi possível gerar o relatório em linguagem natural para este período."

    return texto

  def gerar_relatorio_vendas(self, analise: dict) -> str:
    if not self.api_key:
      raise ValueError("OPENAI_API_KEY não configurada.")

    cliente = OpenAI(api_key=self.api_key)

    prompt = self._montar_prompt_vendas(analise)

    resposta = cliente.responses.create(
      model=self.model,
      input=[
        {
          "role": "system",
          "content": self.system_prompt,
        },
        {"role": "user", "content": prompt},
      ],
      temperature=0.3,
      max_output_tokens=500,
    )

    texto = (resposta.output_text or "").strip()
    if not texto:
      logger.warning("OpenAI não retornou conteúdo textual no relatório.")
      return "Não foi possível gerar o relatório em linguagem natural para este período."

    return texto
  
  def gerar_relatorio_clientes(self, analise: dict) -> str:
    if not self.api_key:
      raise ValueError("OPENAI_API_KEY não configurada.")

    cliente = OpenAI(api_key=self.api_key)

    prompt = self._montar_prompt_clientes(analise)

    resposta = cliente.responses.create(
      model=self.model,
      input=[
        {
          "role": "system",
          "content": self.system_prompt,
        },
        {"role": "user", "content": prompt},
      ],
      temperature=0.3,
      max_output_tokens=500,
    )

    texto = (resposta.output_text or "").strip()
    if not texto:
      logger.warning("OpenAI não retornou conteúdo textual no relatório.")
      return "Não foi possível gerar o relatório em linguagem natural para este período."

    return texto

  def _montar_prompt_compras(self, analise: dict) -> str:
    total_comprado = self._formatar_decimal(analise.get("total_comprado"))

    top_fornecedores = analise.get("top_fornecedores_valor", [])
    top_produtos = analise.get("top_produtos_valor", [])

    linhas_fornecedores = [
      (
        f"- {item.get('fornecedor', 'Fornecedor não identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} "
        f"em {item.get('quantidade_documentos', 0)} documentos"
      )
      for item in top_fornecedores
    ]

    linhas_produtos = [
      (
        f"- {item.get('produto', 'Produto não identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))}, "
        f"quantidade {self._formatar_decimal(item.get('quantidade_total'))}"
      )
      for item in top_produtos
    ]

    periodo_ano = analise.get("periodo_ano")
    periodo_mes = analise.get("periodo_mes")
    periodo = (
      f"{periodo_mes:02d}/{periodo_ano}"
      if periodo_ano and periodo_mes
      else "todos os períodos disponíveis"
    )

    return (
      "Com base nos dados abaixo, gere um relatório com 3 seções: \n"
      "1) Resumo executivo (máx. 5 linhas)\n"
      "2) Principais riscos e oportunidades (bullet points)\n"
      "3) Plano de ação sugerido (3 a 5 ações práticas)\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'não informado')}\n"
      f"Período: {periodo}\n"
      f"Total comprado: R$ {total_comprado}\n\n"
      "Top fornecedores por valor:\n"
      f"{chr(10).join(linhas_fornecedores) if linhas_fornecedores else '- Sem dados'}\n\n"
      "Top produtos por valor:\n"
      f"{chr(10).join(linhas_produtos) if linhas_produtos else '- Sem dados'}"
    )
    
  def _montar_prompt_vendas(self, analise: dict) -> str:
    total_vendido = self._formatar_decimal(analise.get("total_vendido"))

    top_clientes = analise.get("top_clientes_valor", [])
    top_produtos = analise.get("top_produtos_valor", [])

    linhas_clientes = [
      (
        f"- {item.get('cliente', 'Cliente não identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} "
        f"em {item.get('quantidade_documentos', 0)} documentos"
      )
      for item in top_clientes
    ]

    linhas_produtos = [
      (
        f"- {item.get('produto', 'Produto não identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))}, "
        f"quantidade {self._formatar_decimal(item.get('quantidade_total'))}"
      )
      for item in top_produtos
    ]

    periodo_ano = analise.get("periodo_ano")
    periodo_mes = analise.get("periodo_mes")
    periodo = (
      f"{periodo_mes:02d}/{periodo_ano}"
      if periodo_ano and periodo_mes
      else "todos os períodos disponíveis"
    )

    return (
      "Com base nos dados abaixo, gere um relatório com 3 seções: \n"
      "1) Resumo executivo (máx. 5 linhas)\n"
      "2) Principais riscos e oportunidades (bullet points)\n"
      "3) Plano de ação sugerido (3 a 5 ações práticas)\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'não informado')}\n"
      f"Período: {periodo}\n"
      f"Total vendido: R$ {total_vendido}\n\n"
      "Top clientes por valor:\n"
      f"{chr(10).join(linhas_clientes) if linhas_clientes else '- Sem dados'}\n\n"
      "Top produtos por valor:\n"
      f"{chr(10).join(linhas_produtos) if linhas_produtos else '- Sem dados'}"
    )
    
  def _montar_prompt_clientes(self, analise: dict) -> str:
    total_vendido = self._formatar_decimal(analise.get("total_vendido"))
    total_clientes = analise.get("total_clientes", 0)

    top_clientes_valor = analise.get("top_clientes_valor", [])

    linhas_clientes = [
      (
        f"- {item.get('cliente', 'Cliente não identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"{item.get('quantidade_documentos', 0)} documentos | "
        f"ticket médio R$ {self._formatar_decimal(item.get('ticket_medio'))} | "
        f"participação {self._formatar_decimal(item.get('percentual_participacao'))}%"
      )
      for item in top_clientes_valor
    ]

    periodo_ano = analise.get("periodo_ano")
    periodo_mes = analise.get("periodo_mes")
    periodo = (
      f"{periodo_mes:02d}/{periodo_ano}"
      if periodo_ano and periodo_mes
      else "todos os períodos disponíveis"
    )

    return (
      "Com base nos dados abaixo, gere um relatório com 3 seções: \n"
      "1) Resumo executivo (máx. 5 linhas)\n"
      "2) Principais riscos e oportunidades na base de clientes (bullet points)\n"
      "3) Plano de ação sugerido (3 a 5 ações práticas de retenção e expansão)\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'não informado')}\n"
      f"Período: {periodo}\n"
      f"Total vendido: R$ {total_vendido}\n"
      f"Total de clientes no período: {total_clientes}\n\n"
      "Top clientes por valor:\n"
      f"{chr(10).join(linhas_clientes) if linhas_clientes else '- Sem dados'}"
    )
    
  def _carregar_prompt_agente(self) -> str:
    prompt_padrao = (
      "Você é um analista fiscal e financeiro sênior. "
      "Gere um relatório executivo em português do Brasil, objetivo, "
      "com insights acionáveis e linguagem simples para gestores."
    )

    caminho_prompt = Path(__file__).resolve().parent / "Agents" / "Agente_Relatorio_Executivo.txt"
    if not caminho_prompt.exists():
      return prompt_padrao

    try:
      conteudo = caminho_prompt.read_text(encoding="utf-8").strip()
      return conteudo or prompt_padrao
    except Exception as exc:
      logger.warning("Falha ao carregar prompt do agente em %s: %s", caminho_prompt, exc)
      return prompt_padrao

  def _formatar_decimal(self, valor: Decimal | None) -> str:
    if valor is None:
      return "0,00"

    decimal_value = Decimal(str(valor)).quantize(Decimal("0.01"))
    formatted = f"{decimal_value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")