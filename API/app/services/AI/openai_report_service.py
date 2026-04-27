import logging
import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from openai import OpenAI

logger = logging.getLogger("OpenAIReportService")

ReportCategory = Literal["compras", "vendas", "clientes"]
ReportFormat = Literal["executivo", "analitico"]
CONTINUATION_INSTRUCTION = (
  "Continue exatamente de onde a resposta anterior parou, "
  "sem reiniciar, sem resumir e sem repetir blocos ja enviados. "
  "Finalize todo o conteudo restante e feche corretamente todas as tags HTML."
)


class OpenAIReportService:
  def __init__(self):
    self.api_key = os.getenv("OPENAI_API_KEY")
    self.model = os.getenv("OPENAI_REPORT_MODEL", "gpt-4o-mini")

  def disponivel(self) -> bool:
    return bool(self.api_key)

  def gerar_relatorio_compras(
    self,
    analise: dict,
    formato: ReportFormat = "executivo",
    layout: str | None = None,
  ) -> str:
    prompt = self._montar_prompt_compras(analise, formato, layout)
    prompt = self._aplicar_layout_ao_prompt(prompt, layout)
    return self._gerar_relatorio("compras", formato, prompt)

  def gerar_relatorio_vendas(
    self,
    analise: dict,
    formato: ReportFormat = "executivo",
    layout: str | None = None,
  ) -> str:
    prompt = self._montar_prompt_vendas(analise, formato)
    prompt = self._aplicar_layout_ao_prompt(prompt, layout)
    return self._gerar_relatorio("vendas", formato, prompt)

  def gerar_relatorio_clientes(self, analise: dict, formato: ReportFormat = "executivo") -> str:
    prompt = self._montar_prompt_clientes(analise, formato)
    return self._gerar_relatorio("clientes", formato, prompt)

  def _gerar_relatorio(self, categoria: ReportCategory, formato: ReportFormat, prompt: str) -> str:
    if not self.api_key:
      raise ValueError("OPENAI_API_KEY nao configurada.")

    try:
      cliente = OpenAI(api_key=self.api_key)
      system_prompt = self._carregar_prompt_agente(categoria, formato)
      texto = self._gerar_texto_resposta(cliente, system_prompt, prompt, formato)
    except Exception:
      logger.exception(
        "Falha ao gerar relatorio com OpenAI",
        extra={"categoria": categoria, "formato": formato, "model": self.model},
      )
      raise

    if not texto:
      logger.warning("OpenAI nao retornou conteudo textual no relatorio.")
      return "Nao foi possivel gerar o relatorio em linguagem natural para este periodo."

    return texto

  def _gerar_texto_resposta(
    self,
    cliente: OpenAI,
    system_prompt: str,
    prompt: str,
    formato: ReportFormat,
  ) -> str:
    max_tokens = 7000 if formato == "analitico" else 2600

    if hasattr(cliente, "responses"):
      return self._gerar_texto_resposta_responses(
        cliente,
        system_prompt,
        prompt,
        max_tokens,
      )

    return self._gerar_texto_resposta_chat(
      cliente,
      system_prompt,
      prompt,
      max_tokens,
    )

  def _gerar_texto_resposta_responses(
    self,
    cliente: OpenAI,
    system_prompt: str,
    prompt: str,
    max_tokens: int,
  ) -> str:
    partes: list[str] = []
    previous_response_id: str | None = None

    for tentativa in range(3):
      if previous_response_id:
        resposta = cliente.responses.create(
          model=self.model,
          previous_response_id=previous_response_id,
          input=CONTINUATION_INSTRUCTION,
          temperature=0.3,
          max_output_tokens=max_tokens,
        )
      else:
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
          max_output_tokens=max_tokens,
        )

      texto = (getattr(resposta, "output_text", "") or "").strip()
      if texto:
        partes.append(texto)

      previous_response_id = getattr(resposta, "id", None)
      if not self._resposta_foi_truncada(resposta):
        break

      logger.warning(
        "Resposta da OpenAI interrompida por limite; solicitando continuacao.",
        extra={
          "model": self.model,
          "tentativa": tentativa + 1,
          "api": "responses",
        },
      )

    return self._combinar_partes_relatorio(partes)

  def _gerar_texto_resposta_chat(
    self,
    cliente: OpenAI,
    system_prompt: str,
    prompt: str,
    max_tokens: int,
  ) -> str:
    mensagens: list[dict[str, str]] = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": prompt},
    ]
    partes: list[str] = []

    for tentativa in range(3):
      resposta = cliente.chat.completions.create(
        model=self.model,
        messages=mensagens,
        temperature=0.3,
        max_tokens=max_tokens,
      )
      escolha = resposta.choices[0] if resposta.choices else None
      mensagem = escolha.message.content if escolha else ""
      texto = self._extrair_texto_mensagem_chat(mensagem)
      if texto:
        partes.append(texto)
        mensagens.append({"role": "assistant", "content": texto})

      finish_reason = getattr(escolha, "finish_reason", None)
      if finish_reason != "length":
        break

      logger.warning(
        "Resposta da OpenAI interrompida por limite; solicitando continuacao.",
        extra={
          "model": self.model,
          "tentativa": tentativa + 1,
          "api": "chat.completions",
        },
      )
      mensagens.append({"role": "user", "content": CONTINUATION_INSTRUCTION})

    return self._combinar_partes_relatorio(partes)

  def _resposta_foi_truncada(self, resposta) -> bool:
    status = getattr(resposta, "status", None)
    if status == "incomplete":
      return True

    incomplete_details = getattr(resposta, "incomplete_details", None)
    if not incomplete_details:
      return False

    reason = getattr(incomplete_details, "reason", None)
    if reason is None and isinstance(incomplete_details, dict):
      reason = incomplete_details.get("reason")

    return reason in {"max_output_tokens", "length"}

  def _extrair_texto_mensagem_chat(self, mensagem) -> str:
    if isinstance(mensagem, list):
      return "".join(
        parte.get("text", "") if isinstance(parte, dict) else str(parte)
        for parte in mensagem
      ).strip()
    return (mensagem or "").strip()

  def _combinar_partes_relatorio(self, partes: list[str]) -> str:
    if not partes:
      return ""

    relatorio = partes[0]
    for parte in partes[1:]:
      relatorio = f"{relatorio.rstrip()}\n{parte.lstrip()}"
    return relatorio.strip()

  def _montar_prompt_compras(
    self,
    analise: dict,
    formato: ReportFormat,
    layout: str | None = None,
  ) -> str:
    total_comprado = self._formatar_decimal(analise.get("total_comprado"))

    top_fornecedores = analise.get("top_fornecedores_valor", [])
    top_produtos = analise.get("top_produtos_valor", [])

    linhas_fornecedores = [
      (
        f"- {item.get('fornecedor', 'Fornecedor nao identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} "
        f"em {item.get('quantidade_documentos', 0)} documentos"
      )
      for item in top_fornecedores
    ]

    linhas_produtos = [
      (
        f"- {item.get('produto', 'Produto nao identificado')}: "
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
      else "todos os periodos disponiveis"
    )

    return (
      f"Categoria do relatorio: compras\n"
      f"Formato solicitado: {formato}\n"
      f"{self._obter_instrucoes_formato(formato)}\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'nao informado')}\n"
      f"Periodo: {periodo}\n"
      f"Total comprado: R$ {total_comprado}\n\n"
      "Top fornecedores por valor:\n"
      f"{chr(10).join(linhas_fornecedores) if linhas_fornecedores else '- Sem dados'}\n\n"
      "Top produtos por valor:\n"
      f"{chr(10).join(linhas_produtos) if linhas_produtos else '- Sem dados'}"
    )

  def _montar_prompt_vendas(self, analise: dict, formato: ReportFormat) -> str:
    total_vendido_bruto = self._to_decimal(analise.get("total_vendido"))
    total_vendido = self._formatar_decimal(total_vendido_bruto)

    top_clientes = analise.get("top_clientes_valor", [])
    top_produtos = analise.get("top_produtos_valor", [])
    top_regioes = analise.get("top_regioes_valor", [])
    top_cidades = analise.get("top_cidades_valor", [])

    linhas_clientes = [
      (
        f"- {item.get('cliente', 'Cliente nao identificado')}: "
        f"faturamento R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"ticket medio R$ {self._formatar_decimal(self._calcular_ticket_medio(item.get('valor_total'), item.get('quantidade_documentos')))} | "
        f"participacao {self._formatar_percentual(self._calcular_percentual_participacao(item.get('valor_total'), total_vendido_bruto))}%"
      )
      for item in top_clientes
    ]

    linhas_produtos = [
      (
        f"- {item.get('produto', 'Produto nao identificado')}: "
        f"faturamento R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"ticket medio R$ {self._formatar_decimal(self._calcular_ticket_medio(item.get('valor_total'), item.get('quantidade_total')))} | "
        f"participacao {self._formatar_percentual(self._calcular_percentual_participacao(item.get('valor_total'), total_vendido_bruto))}%"
      )
      for item in top_produtos
    ]

    linhas_regioes = [
      (
        f"- {item.get('regiao', 'Regiao nao identificada')}: "
        f"faturamento R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"ticket medio R$ {self._formatar_decimal(self._calcular_ticket_medio(item.get('valor_total'), item.get('quantidade_documentos')))} | "
        f"participacao {self._formatar_percentual(self._calcular_percentual_participacao(item.get('valor_total'), total_vendido_bruto))}%"
      )
      for item in top_regioes
    ]

    linhas_cidades = [
      (
        f"- {item.get('cidade', 'Cidade nao identificada')}: "
        f"faturamento R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"ticket medio R$ {self._formatar_decimal(self._calcular_ticket_medio(item.get('valor_total'), item.get('quantidade_documentos')))} | "
        f"participacao {self._formatar_percentual(self._calcular_percentual_participacao(item.get('valor_total'), total_vendido_bruto))}%"
      )
      for item in top_cidades
    ]

    periodo_ano = analise.get("periodo_ano")
    periodo_mes = analise.get("periodo_mes")
    periodo = (
      f"{periodo_mes:02d}/{periodo_ano}"
      if periodo_ano and periodo_mes
      else "todos os periodos disponiveis"
    )

    return (
      f"Categoria do relatorio: vendas\n"
      f"Formato solicitado: {formato}\n"
      f"{self._obter_instrucoes_formato(formato)}\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'nao informado')}\n"
      f"Periodo: {periodo}\n"
      f"Total vendido: R$ {total_vendido}\n\n"
      "Top regioes por valor:\n"
      f"{chr(10).join(linhas_regioes) if linhas_regioes else '- Sem dados'}\n\n"
      "Top cidades por valor:\n"
      f"{chr(10).join(linhas_cidades) if linhas_cidades else '- Sem dados'}\n\n"
      "Top produtos por valor:\n"
      f"{chr(10).join(linhas_produtos) if linhas_produtos else '- Sem dados'}\n\n"
      "Top clientes por valor:\n"
      f"{chr(10).join(linhas_clientes) if linhas_clientes else '- Sem dados'}"
    )

  def _montar_prompt_clientes(self, analise: dict, formato: ReportFormat) -> str:
    total_vendido = self._formatar_decimal(analise.get("total_vendido"))
    total_clientes = analise.get("total_clientes", 0)
    top_clientes_valor = analise.get("top_clientes_valor", [])

    linhas_clientes = [
      (
        f"- {item.get('cliente', 'Cliente nao identificado')}: "
        f"R$ {self._formatar_decimal(item.get('valor_total'))} | "
        f"ticket medio R$ {self._formatar_decimal(item.get('ticket_medio'))} | "
        f"participacao {self._formatar_decimal(item.get('percentual_participacao'))}%"
      )
      for item in top_clientes_valor
    ]

    periodo_ano = analise.get("periodo_ano")
    periodo_mes = analise.get("periodo_mes")
    periodo = (
      f"{periodo_mes:02d}/{periodo_ano}"
      if periodo_ano and periodo_mes
      else "todos os periodos disponiveis"
    )

    return (
      f"Categoria do relatorio: clientes\n"
      f"Formato solicitado: {formato}\n"
      f"{self._obter_instrucoes_formato(formato)}\n\n"
      f"CNPJ emitente: {analise.get('emitente_cnpj', 'nao informado')}\n"
      f"Periodo: {periodo}\n"
      f"Total vendido: R$ {total_vendido}\n"
      f"Total de clientes no periodo: {total_clientes}\n\n"
      "Top clientes por valor:\n"
      f"{chr(10).join(linhas_clientes) if linhas_clientes else '- Sem dados'}"
    )

  def _carregar_prompt_agente(self, categoria: ReportCategory, formato: ReportFormat) -> str:
    caminho_prompt = Path(__file__).resolve().parent / "Agents" / f"{categoria}_{formato}.txt"
    if not caminho_prompt.exists():
      raise ValueError(
        "Arquivo de prompt nao encontrado: "
        f"{caminho_prompt}. "
        "Verifique se o arquivo de prompt da categoria e formato esta presente."
      )

    try:
      conteudo = caminho_prompt.read_text(encoding="utf-8").strip()
      if not conteudo:
        raise ValueError(
          "Arquivo de prompt vazio: "
          f"{caminho_prompt}. "
          "Preencha o arquivo de prompt correspondente para gerar o relatorio de IA."
        )

      return conteudo
    except Exception as exc:
      if isinstance(exc, ValueError):
        raise

      logger.warning("Falha ao carregar prompt do agente em %s: %s", caminho_prompt, exc)

      raise ValueError(
        "Falha ao carregar arquivo de prompt do agente: "
        f"{caminho_prompt}. "
        "Verifique permissoes e encoding do arquivo."
      ) from exc

  def _obter_instrucoes_formato(self, formato: ReportFormat) -> str:
    if formato == "analitico":
      return (
        "Produza uma resposta mais detalhada, aprofundando a leitura dos numeros, "
        "concentracoes, riscos, oportunidades e recomendacoes."
      )

    return (
      "Produza uma resposta mais enxuta, priorizando sintese executiva, "
      "riscos, oportunidades e acoes de maior impacto."
    )

  def _aplicar_layout_ao_prompt(self, prompt: str, layout: str | None = None) -> str:
    layout_normalizado = (layout or "").strip()
    if not layout_normalizado:
      return prompt

    return (
      f"{prompt}\n\n"
      "Layout solicitado para a saida:\n"
      f"{layout_normalizado}\n\n"
      "Siga esse layout com prioridade na organizacao da resposta, "
      "sem inventar dados fora da base recebida."
    )

  def _to_decimal(self, valor: Decimal | str | int | float | None) -> Decimal:
    if valor is None or valor == "":
      return Decimal("0.00")
    return Decimal(str(valor))

  def _calcular_ticket_medio(
    self,
    valor_total: Decimal | str | int | float | None,
    divisor: Decimal | str | int | float | None,
  ) -> Decimal:
    total = self._to_decimal(valor_total)
    base = self._to_decimal(divisor)
    if base <= 0:
      return Decimal("0.00")
    return (total / base).quantize(Decimal("0.01"))

  def _calcular_percentual_participacao(
    self,
    valor_total: Decimal | str | int | float | None,
    total_geral: Decimal | str | int | float | None,
  ) -> Decimal:
    valor = self._to_decimal(valor_total)
    total = self._to_decimal(total_geral)
    if total <= 0:
      return Decimal("0.00")
    return ((valor / total) * Decimal("100")).quantize(Decimal("0.01"))

  def _formatar_percentual(self, valor: Decimal | str | int | float | None) -> str:
    percentual = self._to_decimal(valor).quantize(Decimal("0.01"))
    formatted = f"{percentual:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

  def _formatar_decimal(self, valor: Decimal | None) -> str:
    if valor is None:
      return "0,00"

    decimal_value = Decimal(str(valor)).quantize(Decimal("0.01"))
    formatted = f"{decimal_value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
