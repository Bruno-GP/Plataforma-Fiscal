import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from openai import OpenAI

logger = logging.getLogger("OpenAIReportService")

ReportCategory = Literal["compras", "vendas", "clientes"]
ReportFormat = Literal["executivo", "analitico"]

class OpenAIReportService:
  def __init__(self):
    self.api_key = os.getenv("OPENAI_API_KEY")
    self.model = os.getenv("OPENAI_REPORT_MODEL", "gpt-4o-mini")

  def disponivel(self) -> bool:
    return bool(self.api_key)

  def gerar_relatorio_compras(self, analise: dict, formato: ReportFormat = "executivo") -> str:
    prompt = self._montar_prompt_compras(analise, formato)
    return self._gerar_relatorio("compras", formato, prompt)

  def gerar_relatorio_vendas(self, analise: dict, formato: ReportFormat = "executivo") -> str:
    prompt = self._montar_prompt_vendas(analise, formato)
    return self._gerar_relatorio("vendas", formato, prompt)

  def gerar_relatorio_clientes(self, analise: dict, formato: ReportFormat = "executivo") -> str:
    prompt = self._montar_prompt_clientes(analise, formato)
    return self._gerar_relatorio("clientes", formato, prompt)

  def _gerar_relatorio(self, categoria: ReportCategory, formato: ReportFormat, prompt: str) -> str:
    if not self.api_key:
      raise ValueError("OPENAI_API_KEY nÃ£o configurada.")

    cliente = OpenAI(api_key=self.api_key)
    system_prompt = self._carregar_prompt_agente(categoria, formato)

    resposta = cliente.responses.create(
      model=self.model,
      input=[
        {
          "role": "system",
          "content": system_prompt,
        },
        {"role": "user", "content": prompt},
      ],
      temperature=0.3,
      max_output_tokens=700 if formato == "analitico" else 500,
    )

    texto = (resposta.output_text or "").strip()
    if not texto:
      logger.warning("OpenAI nÃ£o retornou conteÃºdo textual no relatÃ³rio.")
      return "NÃ£o foi possÃ­vel gerar o relatÃ³rio em linguagem natural para este perÃ­odo."

    return texto

  def _montar_prompt_compras(self, analise: dict, formato: ReportFormat) -> str:
    total_comprado = self._formatar_decimal(analise.get("total_comprado"))

    top_fornecedores = analise.get("top_fornecedores_valor", [])
    top_produtos = analise.get("top_produtos_valor", [])

    linhas_fornecedores = [
      (
        f"- {item.get('fornecedor', 'Fornecedor nÃ£o identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} "
        f"em {item.get('quantidade_documentos', 0)} documentos"
      )
      for item in top_fornecedores
    ]

    linhas_produtos = [
      (
        f"- {item.get('produto', 'Produto nÃ£o identificado')}: "
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
      else "todos os perÃ­odos disponÃ­veis"
    )

    return (
      f"Categoria do relatÃ³rio: compras\n"
      f"Formato solicitado: {formato}\n"
      f"{self._obter_instrucoes_formato(formato)}\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'nÃ£o informado')}\n"
      f"PerÃ­odo: {periodo}\n"
      f"Total comprado: R$ {total_comprado}\n\n"
      "Top fornecedores por valor:\n"
      f"{chr(10).join(linhas_fornecedores) if linhas_fornecedores else '- Sem dados'}\n\n"
      "Top produtos por valor:\n"
      f"{chr(10).join(linhas_produtos) if linhas_produtos else '- Sem dados'}"
    )

  def _montar_prompt_vendas(self, analise: dict, formato: ReportFormat) -> str:
    total_vendido = self._formatar_decimal(analise.get("total_vendido"))

    top_clientes = analise.get("top_clientes_valor", [])
    top_produtos = analise.get("top_produtos_valor", [])

    linhas_clientes = [
      (
        f"- {item.get('cliente', 'Cliente nÃ£o identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} "
        f"em {item.get('quantidade_documentos', 0)} documentos"
      )
      for item in top_clientes
    ]

    linhas_produtos = [
      (
        f"- {item.get('produto', 'Produto nÃ£o identificado')}: "
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
      else "todos os perÃ­odos disponÃ­veis"
    )

    return (
      f"Categoria do relatÃ³rio: vendas\n"
      f"Formato solicitado: {formato}\n"
      f"{self._obter_instrucoes_formato(formato)}\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'nÃ£o informado')}\n"
      f"PerÃ­odo: {periodo}\n"
      f"Total vendido: R$ {total_vendido}\n\n"
      "Top clientes por valor:\n"
      f"{chr(10).join(linhas_clientes) if linhas_clientes else '- Sem dados'}\n\n"
      "Top produtos por valor:\n"
      f"{chr(10).join(linhas_produtos) if linhas_produtos else '- Sem dados'}"
    )

  def _montar_prompt_clientes(self, analise: dict, formato: ReportFormat) -> str:
    total_vendido = self._formatar_decimal(analise.get("total_vendido"))
    total_clientes = analise.get("total_clientes", 0)
    top_clientes_valor = analise.get("top_clientes_valor", [])

    linhas_clientes = [
      (
        f"- {item.get('cliente', 'Cliente nÃ£o identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"{item.get('quantidade_documentos', 0)} documentos | "
        f"ticket mÃ©dio R$ {self._formatar_decimal(item.get('ticket_medio'))} | "
        f"participaÃ§Ã£o {self._formatar_decimal(item.get('percentual_participacao'))}%"
      )
      for item in top_clientes_valor
    ]

    periodo_ano = analise.get("periodo_ano")
    periodo_mes = analise.get("periodo_mes")
    periodo = (
      f"{periodo_mes:02d}/{periodo_ano}"
      if periodo_ano and periodo_mes
      else "todos os perÃ­odos disponÃ­veis"
    )

    return (
      f"Categoria do relatÃ³rio: clientes\n"
      f"Formato solicitado: {formato}\n"
      f"{self._obter_instrucoes_formato(formato)}\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'nÃ£o informado')}\n"
      f"PerÃ­odo: {periodo}\n"
      f"Total vendido: R$ {total_vendido}\n"
      f"Total de clientes no perÃ­odo: {total_clientes}\n\n"
      "Top clientes por valor:\n"
      f"{chr(10).join(linhas_clientes) if linhas_clientes else '- Sem dados'}"
    )

  def _carregar_prompt_agente(self, categoria: ReportCategory, formato: ReportFormat) -> str:
    caminho_prompt = Path(__file__).resolve().parent / "Agents" / f"{categoria}_{formato}.txt"
    if not caminho_prompt.exists():
      raise ValueError(
        "Arquivo de prompt nÃ£o encontrado: "
        f"{caminho_prompt}. "
        "Verifique se o arquivo de prompt da categoria e formato estÃ¡ presente."
      )

    try:
      conteudo = caminho_prompt.read_text(encoding="utf-8").strip()
      if not conteudo:
        raise ValueError(
          "Arquivo de prompt vazio: "
          f"{caminho_prompt}. "
          "Preencha o arquivo de prompt correspondente para gerar o relatÃ³rio de IA."
        )

      return conteudo
    except Exception as exc:
      if isinstance(exc, ValueError):
        raise

      logger.warning("Falha ao carregar prompt do agente em %s: %s", caminho_prompt, exc)

      raise ValueError(
        "Falha ao carregar arquivo de prompt do agente: "
        f"{caminho_prompt}. "
        "Verifique permissÃµes e encoding do arquivo."
      ) from exc

  def _obter_instrucoes_formato(self, formato: ReportFormat) -> str:
    if formato == "analitico":
      return (
        "Produza uma resposta mais detalhada, aprofundando a leitura dos nÃºmeros, "
        "concentraÃ§Ãµes, riscos, oportunidades e recomendaÃ§Ãµes."
      )

    return (
      "Produza uma resposta mais enxuta, priorizando sÃ­ntese executiva, "
      "riscos, oportunidades e aÃ§Ãµes de maior impacto."
    )

  def _formatar_decimal(self, valor: Decimal | None) -> str:
    if valor is None:
      return "0,00"

    decimal_value = Decimal(str(valor)).quantize(Decimal("0.01"))
    formatted = f"{decimal_value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
