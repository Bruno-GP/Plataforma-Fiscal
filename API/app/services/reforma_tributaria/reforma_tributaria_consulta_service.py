from app.core.cache import ttl_cache
from app.repositories.reforma_tributaria.rt_consulta_repository import (
  ReformaTributariaConsultaRepository,
)
from app.services.nfe.postres_config import carregar_config_postgres


DEFAULT_TRIBUTOS: list[dict] = [
  {"id": 7, "codigo": "CBS", "nome": "Contribuicao sobre Bens e Servicos", "esfera": "federal", "tipo": "reforma", "descricao": "Novo tributo federal da Reforma Tributaria do Consumo.", "ativo": True},
  {"id": 8, "codigo": "IBS", "nome": "Imposto sobre Bens e Servicos", "esfera": "compartilhada", "tipo": "reforma", "descricao": "Novo tributo compartilhado entre estados, Distrito Federal e municipios.", "ativo": True},
  {"id": 9, "codigo": "IBS_UF", "nome": "IBS Parcela Estadual", "esfera": "estadual", "tipo": "reforma", "descricao": "Componente estadual do IBS.", "ativo": True},
  {"id": 10, "codigo": "IBS_MUN", "nome": "IBS Parcela Municipal", "esfera": "municipal", "tipo": "reforma", "descricao": "Componente municipal do IBS.", "ativo": True},
  {"id": 11, "codigo": "IS", "nome": "Imposto Seletivo", "esfera": "federal", "tipo": "reforma", "descricao": "Imposto Seletivo incidente sobre bens e servicos especificos.", "ativo": True},
  {"id": 1, "codigo": "ICMS", "nome": "Imposto sobre Circulacao de Mercadorias e Servicos", "esfera": "estadual", "tipo": "atual", "descricao": "Tributo estadual vigente antes da Reforma Tributaria do Consumo.", "ativo": True},
  {"id": 2, "codigo": "ICMS_ST", "nome": "ICMS Substituicao Tributaria", "esfera": "estadual", "tipo": "atual", "descricao": "Modalidade de recolhimento por substituicao tributaria do ICMS.", "ativo": True},
  {"id": 3, "codigo": "IPI", "nome": "Imposto sobre Produtos Industrializados", "esfera": "federal", "tipo": "atual", "descricao": "Tributo federal vigente antes da Reforma Tributaria do Consumo.", "ativo": True},
  {"id": 4, "codigo": "PIS", "nome": "Programa de Integracao Social", "esfera": "federal", "tipo": "atual", "descricao": "Contribuicao federal a ser substituida/absorvida no contexto da CBS.", "ativo": True},
  {"id": 5, "codigo": "COFINS", "nome": "Contribuicao para o Financiamento da Seguridade Social", "esfera": "federal", "tipo": "atual", "descricao": "Contribuicao federal a ser substituida/absorvida no contexto da CBS.", "ativo": True},
  {"id": 6, "codigo": "ISS", "nome": "Imposto sobre Servicos", "esfera": "municipal", "tipo": "atual", "descricao": "Tributo municipal vigente antes da Reforma Tributaria do Consumo.", "ativo": True},
]


class ReformaTributariaConsultaService:
  def __init__(self) -> None:
    config = carregar_config_postgres()
    self.conn_params = {
      "host": config["host"],
      "port": config["port"],
      "dbname": config["database"],
      "user": config["user"],
      "password": config["password"],
      "connect_timeout": 5,
    }

    if config.get("conninfo"):
      self.conn_params = {
        "conninfo": config["conninfo"],
        "connect_timeout": 5,
      }

    if config.get("sslmode"):
      self.conn_params["sslmode"] = config["sslmode"]
    self.repository = ReformaTributariaConsultaRepository(self.conn_params)

  @ttl_cache(ttl_seconds=300, maxsize=32)
  def listar_tributos(self, incluir_inativos: bool = False) -> list[dict]:
    if not incluir_inativos:
      return [dict(tributo) for tributo in DEFAULT_TRIBUTOS]
    return self.repository.listar_tributos(incluir_inativos=incluir_inativos)

  def listar_apuracoes(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    tributo_codigo: str | None = None,
  ) -> list[dict]:
    return self.repository.listar_apuracoes(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      tributo_codigo=tributo_codigo,
    )

  def listar_documento_tributos(
    self,
    emitente_cnpj: str,
    origem_documento: str,
    documento_id: int,
  ) -> list[dict]:
    return self.repository.listar_documento_tributos(
      emitente_cnpj=emitente_cnpj,
      origem_documento=origem_documento,
      documento_id=documento_id,
    )

  def listar_item_tributos(
    self,
    emitente_cnpj: str,
    origem_item: str,
    item_id: int,
  ) -> list[dict]:
    return self.repository.listar_item_tributos(
      emitente_cnpj=emitente_cnpj,
      origem_item=origem_item,
      item_id=item_id,
    )

  def listar_memoria_calculo(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    tributo_codigo: str | None = None,
    documento_tributo_id: int | None = None,
    item_tributo_id: int | None = None,
    limite: int = 100,
    offset: int = 0,
  ) -> list[dict]:
    return self.repository.listar_memoria_calculo(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      tributo_codigo=tributo_codigo,
      documento_tributo_id=documento_tributo_id,
      item_tributo_id=item_tributo_id,
      limite=limite,
      offset=offset,
    )

  def contar_memoria_calculo(
    self,
    emitente_cnpj: str,
    periodo_ano: int | None = None,
    periodo_mes: int | None = None,
    tributo_codigo: str | None = None,
    documento_tributo_id: int | None = None,
    item_tributo_id: int | None = None,
  ) -> int:
    return self.repository.contar_memoria_calculo(
      emitente_cnpj=emitente_cnpj,
      periodo_ano=periodo_ano,
      periodo_mes=periodo_mes,
      tributo_codigo=tributo_codigo,
      documento_tributo_id=documento_tributo_id,
      item_tributo_id=item_tributo_id,
    )
