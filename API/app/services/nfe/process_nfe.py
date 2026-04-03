from datetime import datetime
from xml.etree import ElementTree as ET

import psycopg
import logging

from app.services.nfe.postres_config import carregar_config_postgres

from app.models.nfe.schemas import (
    ProcessarNFeRequest,
    ProcessarNFeResponse,
    ErroProcessamento,
    KPIPorPeriodo
)

from app.domain.nfe.xml_reader import XmlReader, extrair_emitente_xml, classificar_xml_processavel
from app.domain.nfe.xml_models import XmlNFe
from app.domain.nfe.extractor import NFeExtractor
from app.domain.nfe.consolidator import NFeConsolidator
from app.domain.nfe.kpis import KPICalculator
from app.services.nfe.empresa_service import EmpresaService, normalizar_cnpj
from app.services.nfe.nfe_notas_service import NFeNotasService
from app.services.nfe.nfe_itens_service import NFeItensService
from app.services.nfe.nfe_process_service import NFeProcessamentosService

logger = logging.getLogger("ProcessarNFeService")

class ProcessarNFeService:
    def _registrar_progresso(self, percentual: int) -> None:
        percentual_normalizado = max(0, min(100, percentual))
        ultimo_percentual = getattr(self, "_ultimo_progresso", 0)
        if percentual_normalizado <= ultimo_percentual:
            return
        self._ultimo_progresso = percentual_normalizado
        logger.info("Processamento em %s%%", percentual_normalizado)

    def _registrar_notas_por_modelo(
        self,
        conn,
        notas,
        processamento_id: int,
    ) -> int:
        notas_service = NFeNotasService()
        notas_nfse, notas_demais_modelos = notas_service.separar_notas_por_modelo(notas)

        total_registrado = 0

        if notas_demais_modelos:
            total_registrado += notas_service.registrar_notas(
                conn=conn,
                notas=notas_demais_modelos,
                processamento_id=processamento_id,
            )
            NFeItensService().registrar_itens(
                conn=conn,
                notas=notas_demais_modelos,
            )

        if notas_nfse:
            total_registrado += notas_service.registrar_notas(
                conn=conn,
                notas=notas_nfse,
                processamento_id=processamento_id,
            )
            NFeItensService().registrar_itens(
                conn=conn,
                notas=notas_nfse,
            )

        return total_registrado

    
    def executar(self, request: ProcessarNFeRequest) -> ProcessarNFeResponse:
        xmls = XmlReader().ler_pasta(request.pasta_xml)
        return self._executar_com_xmls(
            xmls=xmls,
            request=request,
        )

    def executar_xmls_importados(
        self,
        cnpj_emitente: str,
        xmls_importados: list[tuple[int, str, bytes]],
    ) -> tuple[ProcessarNFeResponse, list[int]]:
        cnpj_emitente_normalizado = normalizar_cnpj(cnpj_emitente)
        if not cnpj_emitente_normalizado:
            cnpj_emitente_normalizado = cnpj_emitente
            
        ids_processados: list[int] = []
        xmls = []

        for xml_id, nome_arquivo, conteudo in xmls_importados:
            if not conteudo:
                continue

            try:
                root = ET.fromstring(conteudo)
            except ET.ParseError:
                continue

            processavel, _ = classificar_xml_processavel(root)
            if not processavel:
                continue

            cnpj_extraido, nome_emitente = extrair_emitente_xml(root)
            cnpj_xml = normalizar_cnpj(cnpj_extraido)

            if not cnpj_xml or cnpj_xml != cnpj_emitente_normalizado:
                continue

            xmls.append(
                XmlNFe(
                    caminho=nome_arquivo,
                    xml=root,
                    emitente_cnpj=cnpj_xml,
                    emitente_nome=nome_emitente or "",
                )
            )
            ids_processados.append(xml_id)

        request = ProcessarNFeRequest(
            origem="upload_xml",
            pasta_xml="notas_xml_importados",
            periodo=None,
        )

        return self._executar_com_xmls(xmls=xmls, request=request), ids_processados

    def _executar_com_xmls(
        self,
        xmls,
        request: ProcessarNFeRequest,
    ) -> ProcessarNFeResponse:
        
        cnpj_emitente = ""
        periodo_ano = 0
        periodo_mes = 0
        periodos_encontrados = []
        erros_processamento = []

        try:
            self._ultimo_progresso = 0
            # 1️⃣ Ler XMLs
            if not xmls:
                raise Exception("Nenhum XML válido encontrado")

            logger.info("Processamento iniciado")
            self._registrar_progresso(10)

            # 2️⃣ Extrair notas
            notas = NFeExtractor().extrair(xmls)
            if not notas:
                raise Exception("Nenhuma NFe válida extraída")
            self._registrar_progresso(20)

            # 3️⃣ Determinar períodos
            periodos = {
                (n.data_emissao.year, n.data_emissao.month)
                for n in notas
            }
            
            periodos_ordenados = sorted(periodos)

            periodos_encontrados = [
                {"ano": ano, "mes": mes}
                for ano, mes in periodos_ordenados
            ]

            if len(periodos_ordenados) == 1:
                periodo_ano, periodo_mes = periodos_ordenados[0]
            self._registrar_progresso(30)

            # 4️⃣ Identificar CNPJ emitente
            cnpjs = {n.emitente_cnpj for n in notas}
            if len(cnpjs) != 1:
                raise Exception("Mais de um CNPJ de emitente encontrado")

            cnpj_emitente = cnpjs.pop()

            # 5️⃣ Identificar nome do emitente
            nomes_emitente = {
                xml.emitente_nome.strip()
                for xml in xmls
                if xml.emitente_nome
            }
            if not nomes_emitente:
                raise Exception("Nome do emitente não encontrado")

            nome_emitente = next(iter(nomes_emitente))
            self._registrar_progresso(40)

            # 6️⃣ Consolidar notas e itens
            consolidacao = NFeConsolidator().consolidar(notas)
            self._registrar_progresso(50)

            # 7️⃣ Registrar empresa
            empresa_id = request.empresa_id
            if not empresa_id:
                empresa_id = EmpresaService().obter_ou_criar(
                    cnpj_emitente=cnpj_emitente,
                    nome_emitente=nome_emitente
                )
            self._registrar_progresso(60)

            # 🔟 Calcular KPIs (total e por período)
            kpi_calculator = KPICalculator()
            notas_por_periodo = {}
            for nota in notas:
                chave_periodo = (nota.data_emissao.year, nota.data_emissao.month)
                notas_por_periodo.setdefault(chave_periodo, []).append(nota)
                
            kpis_por_periodo = []

            # 1️⃣1️⃣ Registrar processamento por período
            processamento_service = NFeProcessamentosService()
            self._registrar_progresso(70)

            for indice, (ano, mes) in enumerate(periodos_ordenados):
                notas_periodo = notas_por_periodo.get((ano, mes), [])

                if not notas_periodo:
                    continue

                itens_periodo = sum(len(nota.itens) for nota in notas_periodo)

                # Registrar processamento
                config = carregar_config_postgres()

                with psycopg.connect(
                    host=config["host"],
                    port=config["port"],
                    dbname=config["database"],
                    user=config["user"],
                    password=config["password"],
                ) as conn:

                    with conn.transaction():

                        processamento_id = processamento_service.registrar_processamento(
                            conn=conn,
                            empresa_id=empresa_id,
                            cnpj_emitente=cnpj_emitente,
                            periodo_ano=ano,
                            periodo_mes=mes,
                            origem=request.origem,
                            pasta_xml=request.pasta_xml,
                            periodo_solicitado=request.periodo,
                            periodos_encontrados=None,
                            notas_processadas=len(notas_periodo),
                            itens_processados=itens_periodo,
                            status="processado",
                            data_processamento=datetime.utcnow()
                        )

                        if not processamento_id:
                            raise Exception("Processamento não registrado")
                        
                        self._registrar_notas_por_modelo(
                            conn=conn,
                            notas=notas_periodo,
                            processamento_id=processamento_id,
                        )
                        self._registrar_progresso(80)
                        
                        notas_service = NFeNotasService()
                        
                        notas_para_kpi = notas_service.listar_notas_periodo_para_kpi(
                            conn=conn,
                            cnpj_emitente=cnpj_emitente,
                            periodo_ano=ano,
                            periodo_mes=mes,
                        )
                        notas_venda_para_kpi = notas_service.filtrar_notas_com_cfop_venda(
                            conn=conn,
                            notas=notas_para_kpi,
                        )
                        kpis_periodo = kpi_calculator.calcular(notas_venda_para_kpi)

                        kpi_calculator.registrar_kpis(
                            processamento_id=processamento_id,
                            emitente_cnpj=cnpj_emitente,
                            periodo_ano=ano,
                            periodo_mes=mes,
                            kpis=kpis_periodo,
                            conn=conn,
                        )
                        self._registrar_progresso(90)
                
                # 🔹 Converter dict de KPIs para o schema correto do response
                kpis_relatorio = kpis_periodo

                kpis_por_periodo.append(
                    KPIPorPeriodo(
                        ano=ano,
                        mes=mes,
                        kpis=kpis_relatorio
                    )
                )
                
            self._registrar_progresso(100)
            logger.info("Processamento finalizado")

            # ✅ RETORNO DE SUCESSO (ERA ISSO QUE FALTAVA)
            return ProcessarNFeResponse(
                status="processado",
                cnpj_emitente=cnpj_emitente,
                periodo_ano=periodo_ano,
                periodo_mes=periodo_mes,
                periodos_encontrados=periodos_encontrados,
                notas_processadas=consolidacao.notas_processadas,
                itens_processados=consolidacao.itens_processados,
                kpis=kpis_por_periodo,
                erros=erros_processamento,
                data_processamento=datetime.utcnow().isoformat()
            )


        except Exception as exc:
            erros = list(erros_processamento)
            erros.append(
                ErroProcessamento(
                    codigo="PROCESSAMENTO_NFE_ERRO",
                    mensagem=str(exc)
                ).model_dump()
            )
            logger.error("Falha durante o processamento dos XMLs: %s", exc)
            
            return ProcessarNFeResponse(
                status="erro",
                cnpj_emitente=cnpj_emitente,
                periodo_ano=periodo_ano,
                periodo_mes=periodo_mes,
                periodos_encontrados=periodos_encontrados,
                notas_processadas=0,
                itens_processados=0,
                kpis=[],
                erros=erros,
                data_processamento=datetime.utcnow().isoformat()
            )
