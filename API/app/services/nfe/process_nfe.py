from datetime import datetime

import psycopg
from app.services.nfe.postres_config import carregar_config_postgres

from app.models.nfe.schemas import (
    ProcessarNFeRequest,
    ProcessarNFeResponse,
    ErroProcessamento,
    KPIPorPeriodo, 
    KPIsRelatorio
)

from app.domain.nfe.xml_reader import XmlReader
from app.domain.nfe.extractor import NFeExtractor
from app.domain.nfe.consolidator import NFeConsolidator
from app.domain.nfe.kpis import KPICalculator
from app.services.nfe.empresa_service import EmpresaService
from app.services.nfe.nfe_notas_service import NFeNotasService
from app.services.nfe.nfe_itens_service import NFeItensService
from app.services.nfe.nfe_process_service import NFeProcessamentosService

class ProcessarNFeService:
    def executar(self, request: ProcessarNFeRequest) -> ProcessarNFeResponse:
        cnpj_emitente = ""
        periodo_ano = 0
        periodo_mes = 0
        periodos_encontrados = []
        erros_processamento = []

        try:
            # 1️⃣ Ler XMLs
            xmls = XmlReader().ler_pasta(request.pasta_xml)
            if not xmls:
                raise Exception("Nenhum XML válido encontrado")

            # 2️⃣ Extrair notas
            notas = NFeExtractor().extrair(xmls)
            if not notas:
                raise Exception("Nenhuma NFe válida extraída")

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

            # 6️⃣ Consolidar notas e itens
            consolidacao = NFeConsolidator().consolidar(notas)

            # 7️⃣ Registrar empresa
            empresa_id = request.empresa_id
            if not empresa_id:
                empresa_id = EmpresaService().obter_ou_criar(
                    cnpj_emitente=cnpj_emitente,
                    nome_emitente=nome_emitente
                )

            # 🔟 Calcular KPIs (total e por período)
            kpi_calculator = KPICalculator()
            notas_por_periodo = {}
            for nota in notas:
                chave_periodo = (nota.data_emissao.year, nota.data_emissao.month)
                notas_por_periodo.setdefault(chave_periodo, []).append(nota)
                
            kpis_por_periodo = []

            # 1️⃣1️⃣ Registrar processamento por período
            processamento_service = NFeProcessamentosService()

            for ano, mes in periodos_ordenados:
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

                        NFeNotasService().registrar_notas(
                            conn=conn,
                            notas=notas_periodo
                        )

                        NFeItensService().registrar_itens(
                            conn=conn,
                            notas=notas_periodo
                        )

                        kpi_calculator.registrar_kpis(
                            conn=conn,
                            processamento_id=processamento_id,
                            emitente_cnpj=cnpj_emitente,
                            periodo_ano=ano,
                            periodo_mes=mes,
                            kpis=kpis_periodo
                        )
                
                # 🔹 Converter dict de KPIs para o schema correto do response
                kpis_relatorio = KPIsRelatorio(**kpis_periodo)

                kpis_por_periodo.append(
                    KPIPorPeriodo(
                        ano=ano,
                        mes=mes,
                        kpis=kpis_relatorio
                    )
                )


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
