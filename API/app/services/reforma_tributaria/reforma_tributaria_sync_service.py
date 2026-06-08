import psycopg
import logging

from app.domain.nfe.extractor import NS, _extrair_tributos_reforma_item, _parse_data_emissao
from app.repositories.reforma_tributaria.resumo_repository import coletar_resumo_periodo
from app.repositories.reforma_tributaria.rt_sync_repository import ReformaTributariaSyncRepository
from app.repositories.reforma_tributaria.xml_importado_repository import (
  inserir_tributo_reforma_item_importado,
  remover_tributos_reforma_nota,
)
from app.services.nfe.empresa_service import normalizar_cnpj
from app.services.nfe.nfe_itens_service import NFeItensService
from app.services.reforma_tributaria.xml_helpers import (
  encontrar_elemento_local,
  encontrar_filho_local,
  encontrar_filhos_local,
  normalizar_numero_nf,
  parse_xml_importado,
  texto_filho_local,
)


logger = logging.getLogger("ReformaTributariaSyncService")
# logger.setLevel(logging.INFO)


_rt_sync_repository = ReformaTributariaSyncRepository()


class ReformaTributariaSyncService:
  """Sincroniza dados fiscais consolidados para as tabelas da Reforma Tributária."""

  TRIBUTOS_LEGADOS_NFE = ("ICMS", "IPI", "PIS", "COFINS")
  TRIBUTOS_LEGADOS_SPED = ("ICMS",)
  TRIBUTOS_REFORMA = ("CBS", "IBS", "IBS_UF", "IBS_MUN", "IS")

  def sincronizar_nfe_todos_periodos(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
  ) -> list[dict]:
    """Reprocessa todos os períodos NFe encontrados para recompor apuração/memória."""

    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      # logger.warning("Backfill NFe ignorado: CNPJ invalido recebido=%s", emitente_cnpj)
      return []

    # logger.info("Backfill NFe iniciado: cnpj=%s", cnpj)
    with conn.cursor() as cur:
      periodos = _rt_sync_repository.listar_periodos_nfe(cur, cnpj)

    # logger.info("Backfill NFe periodos encontrados: cnpj=%s total_periodos=%s", cnpj, len(periodos))
    resultados = []
    for periodo_ano, periodo_mes, documentos in periodos:
      # logger.info(
      #   "Backfill NFe periodo iniciado: cnpj=%s periodo=%04d-%02d documentos=%s",
      #   cnpj,
      #   periodo_ano,
      #   periodo_mes,
      #   documentos,
      # )
      resumo = self.sincronizar_nfe_periodo(
        conn=conn,
        emitente_cnpj=cnpj,
        periodo_ano=periodo_ano,
        periodo_mes=periodo_mes,
      )
      resultados.append(
        {
          "origem": "nfe",
          "periodo_ano": periodo_ano,
          "periodo_mes": periodo_mes,
          "documentos": documentos,
          **resumo,
        }
      )
      # logger.info(
      #   "Backfill NFe periodo finalizado: cnpj=%s periodo=%04d-%02d resumo=%s",
      #   cnpj,
      #   periodo_ano,
      #   periodo_mes,
      #   resumo,
      # )

    # logger.info("Backfill NFe finalizado: cnpj=%s periodos_processados=%s", cnpj, len(resultados))
    return resultados

  def sincronizar_sped_todos_periodos(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
  ) -> list[dict]:
    """Atualiza apuração e memória SPED para todos os períodos já carregados."""

    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      # logger.warning("Backfill SPED ignorado: CNPJ invalido recebido=%s", emitente_cnpj)
      return []

    # logger.info("Backfill SPED iniciado: cnpj=%s", cnpj)
    with conn.cursor() as cur:
      periodos = _rt_sync_repository.listar_periodos_sped(cur, cnpj)

    self.sincronizar_sped_apuracao_icms(conn=conn, emitente_cnpj=cnpj)
    self.sincronizar_sped_documentos_itens_icms(conn=conn, emitente_cnpj=cnpj)

    resultados = []
    with conn.cursor() as cur:
      for periodo_ano, periodo_mes, documentos in periodos:
        resumo = coletar_resumo_periodo(cur, cnpj, periodo_ano, periodo_mes, "sped")
        resultado = {
          "origem": "sped",
          "periodo_ano": periodo_ano,
          "periodo_mes": periodo_mes,
          "documentos": documentos,
          **resumo,
        }
        resultados.append(resultado)
        # logger.info(
        #   "Backfill SPED periodo finalizado: cnpj=%s periodo=%04d-%02d resumo=%s",
        #   cnpj,
        #   periodo_ano,
        #   periodo_mes,
        #   resumo,
        # )

    # logger.info("Backfill SPED finalizado: cnpj=%s periodos_processados=%s", cnpj, len(resultados))
    return resultados

  def sincronizar_nfe_periodo(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> dict:
    """Recria a visão tributária NFe do período a partir de notas, itens e XMLs importados."""

    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      # logger.warning("Sincronizacao NFe ignorada: CNPJ invalido recebido=%s", emitente_cnpj)
      return {}

    with conn.cursor() as cur:
      self._garantir_tributos_base(cur)
      # logger.info("Sincronizacao NFe limpando tributos legados: cnpj=%s periodo=%04d-%02d", cnpj, periodo_ano, periodo_mes)
      self._remover_tributos_nfe_periodo(cur, cnpj, periodo_ano, periodo_mes)
      self._remover_creditos_debitos_nfe_periodo(
        cur,
        cnpj,
        periodo_ano,
        periodo_mes,
        self.TRIBUTOS_LEGADOS_NFE + self.TRIBUTOS_REFORMA,
      )
      self._remover_memoria_nfe_periodo(
        cur,
        cnpj,
        periodo_ano,
        periodo_mes,
        self.TRIBUTOS_LEGADOS_NFE + self.TRIBUTOS_REFORMA,
      )
      # logger.info("Sincronizacao NFe inserindo documentos/itens legados: cnpj=%s periodo=%04d-%02d", cnpj, periodo_ano, periodo_mes)
      self._inserir_documentos_tributos_nfe(cur, cnpj, periodo_ano, periodo_mes)
      self._inserir_itens_tributos_nfe(cur, cnpj, periodo_ano, periodo_mes)
      xml_resumo = self._inserir_tributos_reforma_xml_importados(cur, cnpj, periodo_ano, periodo_mes)
      # logger.info(
      #   "Sincronizacao NFe XMLs importados processados: cnpj=%s periodo=%04d-%02d resumo=%s",
      #   cnpj,
      #   periodo_ano,
      #   periodo_mes,
      #   xml_resumo,
      # )
      # logger.info("Sincronizacao NFe gerando creditos/debitos/memoria/apuracao: cnpj=%s periodo=%04d-%02d", cnpj, periodo_ano, periodo_mes)
      self._inserir_creditos_debitos_nfe(
        cur,
        cnpj,
        periodo_ano,
        periodo_mes,
        self.TRIBUTOS_LEGADOS_NFE + self.TRIBUTOS_REFORMA,
      )
      self._inserir_memoria_nfe(cur, cnpj, periodo_ano, periodo_mes)
      self._atualizar_apuracao_nfe(cur, cnpj, periodo_ano, periodo_mes)
      resumo = coletar_resumo_periodo(cur, cnpj, periodo_ano, periodo_mes, "xml")
      return {**xml_resumo, **resumo}

  def sincronizar_sped_apuracao_icms(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
  ) -> None:
    """Replica a apuração ICMS do SPED para a tabela unificada da Reforma Tributária."""

    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      return

    with conn.cursor() as cur:
      _rt_sync_repository.sincronizar_sped_apuracao_icms(cur, cnpj)

  def sincronizar_sped_documentos_itens_icms(
    self,
    conn: psycopg.Connection,
    emitente_cnpj: str,
  ) -> None:
    """Recria documentos, itens, créditos/débitos e memória ICMS derivados do SPED."""

    cnpj = normalizar_cnpj(emitente_cnpj)
    if not cnpj:
      return

    with conn.cursor() as cur:
      self._garantir_tributos_base(cur)
      self._remover_tributos_sped(cur, cnpj)
      self._inserir_documentos_tributos_sped_icms(cur, cnpj)
      self._inserir_itens_tributos_sped_icms(cur, cnpj)
      self._inserir_creditos_debitos_sped_icms(cur, cnpj)
      self._inserir_memoria_sped_icms(cur, cnpj)

  def _garantir_tributos_base(self, cur) -> None:
    _rt_sync_repository.garantir_tributos_base(cur)

  def _remover_tributos_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    _rt_sync_repository.remover_tributos_nfe_periodo(cur, cnpj, periodo_ano, periodo_mes)

  def _remover_tributos_sped(self, cur, cnpj: str) -> None:
    _rt_sync_repository.remover_tributos_sped(cur, cnpj)

  def _inserir_documentos_tributos_sped_icms(self, cur, cnpj: str) -> None:
    _rt_sync_repository.inserir_documentos_tributos_sped_icms(cur, cnpj)

  def _inserir_itens_tributos_sped_icms(self, cur, cnpj: str) -> None:
    _rt_sync_repository.inserir_itens_tributos_sped_icms(cur, cnpj)

  def _inserir_creditos_debitos_sped_icms(self, cur, cnpj: str) -> None:
    _rt_sync_repository.inserir_creditos_debitos_sped_icms(cur, cnpj)

  def _inserir_memoria_sped_icms(self, cur, cnpj: str) -> None:
    _rt_sync_repository.inserir_memoria_sped_icms(cur, cnpj)

  def _remover_creditos_debitos_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    codigos_tributos: tuple[str, ...],
  ) -> None:
    _rt_sync_repository.remover_creditos_debitos_nfe_periodo(
      cur,
      cnpj,
      periodo_ano,
      periodo_mes,
      codigos_tributos,
    )

  def _remover_memoria_nfe_periodo(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    codigos_tributos: tuple[str, ...],
  ) -> None:
    _rt_sync_repository.remover_memoria_nfe_periodo(
      cur,
      cnpj,
      periodo_ano,
      periodo_mes,
      codigos_tributos,
    )

  def _inserir_documentos_tributos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    _rt_sync_repository.inserir_documentos_tributos_nfe(cur, cnpj, periodo_ano, periodo_mes)

  def _inserir_itens_tributos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    _rt_sync_repository.inserir_itens_tributos_nfe(cur, cnpj, periodo_ano, periodo_mes)

  def _inserir_tributos_reforma_xml_importados(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> dict:
    """Extrai CBS/IBS/IS diretamente dos XMLs importados para complementar a base NFe."""

    resumo = {
      "xmls_importados_lidos": 0,
      "xmls_periodo": 0,
      "xmls_com_reforma": 0,
      "notas_reforma_reconstruidas": 0,
      "itens_reforma_xml": 0,
      "tributos_reforma_inseridos": 0,
    }

    if not _rt_sync_repository.tabela_xml_importados_existe(cur):
      return resumo

    xmls_importados = _rt_sync_repository.listar_xmls_importados(cur, cnpj)
    resumo["xmls_importados_lidos"] = len(xmls_importados)
    if not xmls_importados:
      return resumo

    nota_ids_reforma: set[int] = set()
    notas_reconstruidas: set[int] = set()

    for xml_id, nome_arquivo, conteudo_xml in xmls_importados:
      root = parse_xml_importado(conteudo_xml)
      if root is None:
        continue

      inf = root.find(".//nfe:infNFe", NS) or encontrar_elemento_local(root, "infNFe")
      if inf is None:
        continue

      ide = inf.find("nfe:ide", NS) or encontrar_filho_local(inf, "ide")
      emit = inf.find("nfe:emit", NS) or encontrar_filho_local(inf, "emit")
      if ide is None or emit is None:
        continue

      emitente_xml = normalizar_cnpj(
        texto_filho_local(emit, "CNPJ") or texto_filho_local(emit, "CPF")
      )
      if emitente_xml != cnpj:
        continue

      numero_nf = normalizar_numero_nf(texto_filho_local(ide, "nNF"))
      modelo = texto_filho_local(ide, "mod")
      dh_emi = texto_filho_local(ide, "dhEmi")
      d_emi = texto_filho_local(ide, "dEmi")
      if not numero_nf or not (dh_emi or d_emi):
        continue

      try:
        data_emissao = _parse_data_emissao(dh_emi, d_emi)
      except ValueError:
        continue

      if data_emissao.year != periodo_ano or data_emissao.month != periodo_mes:
        continue

      resumo["xmls_periodo"] += 1
      xml_tem_reforma = False

      for det in encontrar_filhos_local(inf, "det"):
        tributos_reforma = _extrair_tributos_reforma_item(det)
        if not tributos_reforma:
          continue

        xml_tem_reforma = True
        prod = det.find("nfe:prod", NS) or encontrar_filho_local(det, "prod")
        numero_item = int(det.attrib.get("nItem") or 0)
        produto_codigo = texto_filho_local(prod, "cProd") if prod is not None else ""
        ncm = texto_filho_local(prod, "NCM") if prod is not None else ""
        cfop = texto_filho_local(prod, "CFOP") if prod is not None else ""

        item_row = _rt_sync_repository.buscar_item_nfe_para_xml_importado(
          cur,
          cnpj,
          str(numero_nf),
          modelo,
          data_emissao,
          numero_item,
          produto_codigo,
        )
        if not item_row:
          continue

        nota_id, nota_item_id, empresa_cnpj = item_row
        nota_id = int(nota_id)
        if nota_id not in notas_reconstruidas:
          remover_tributos_reforma_nota(
            cur,
            nota_id=nota_id,
            codigos_tributos=self.TRIBUTOS_REFORMA,
          )
          notas_reconstruidas.add(nota_id)

        inseriu_item = False
        for tributo in tributos_reforma:
          if inserir_tributo_reforma_item_importado(
            cur=cur,
            nota_item_id=int(nota_item_id),
            empresa_cnpj=empresa_cnpj,
            periodo_ano=periodo_ano,
            periodo_mes=periodo_mes,
            numero_item=numero_item,
            produto_codigo=produto_codigo,
            ncm=ncm,
            cfop=cfop,
            tributo=tributo,
          ):
            inseriu_item = True
            resumo["tributos_reforma_inseridos"] += 1

        if inseriu_item:
          resumo["itens_reforma_xml"] += 1
          nota_ids_reforma.add(nota_id)

      if xml_tem_reforma:
        resumo["xmls_com_reforma"] += 1

    if nota_ids_reforma:
      NFeItensService()._registrar_documentos_reforma_agregados(
        cur,
        sorted(nota_ids_reforma),
      )

    resumo["notas_reforma_reconstruidas"] = len(nota_ids_reforma)
    return resumo

  def _inserir_creditos_debitos_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
    codigos_tributos: tuple[str, ...],
  ) -> None:
    _rt_sync_repository.inserir_creditos_debitos_nfe(
      cur,
      cnpj,
      periodo_ano,
      periodo_mes,
      codigos_tributos,
    )

  def _inserir_memoria_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    _rt_sync_repository.inserir_memoria_nfe(cur, cnpj, periodo_ano, periodo_mes)

  def _atualizar_apuracao_nfe(
    self,
    cur,
    cnpj: str,
    periodo_ano: int,
    periodo_mes: int,
  ) -> None:
    _rt_sync_repository.atualizar_apuracao_nfe(cur, cnpj, periodo_ano, periodo_mes)

