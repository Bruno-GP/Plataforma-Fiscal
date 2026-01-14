from datetime import datetime

from app.models.schemas import (
    ProcessarNFeRequest,
    ProcessarNFeResponse,
    ErroProcessamento,
    KPIsRelatorio
)

from app.domain.xml_reader import XmlReader
from app.domain.extractor import NFeExtractor
from app.domain.consolidator import NFeConsolidator
from app.domain.kpis import KPICalculator
from app.services.empresa_service import EmpresaService
from app.services.nfe_notas_service import NFeNotasService
from app.services.nfe_itens_service import NFeItensService
from app.services.nfe_process_service import NFeProcessamentosService

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

            periodos_encontrados = [
                {"ano": ano, "mes": mes}
                for ano, mes in sorted(periodos)
            ]

            if len(periodos) == 1:
                periodo_ano = periodos_encontrados[0]["ano"]
                periodo_mes = periodos_encontrados[0]["mes"]

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

            # 8️⃣ Registrar notas
            NFeNotasService().registrar_notas(consolidacao.notas)

            # 9️⃣ Registrar itens
            NFeItensService().registrar_itens(consolidacao.notas)

            # 🔟 Calcular KPIs
            kpis = KPICalculator().calcular(consolidacao.notas)

            # 1️⃣1️⃣ Registrar processamento
            processamento_id = NFeProcessamentosService().registrar_processamento(
                empresa_id=empresa_id,
                cnpj_emitente=cnpj_emitente,
                periodo_ano=periodo_ano,
                periodo_mes=periodo_mes,
                origem=request.origem,
                pasta_xml=request.pasta_xml,
                periodo_solicitado=request.periodo,
                periodos_encontrados=periodos_encontrados,
                notas_processadas=consolidacao.notas_processadas,
                itens_processados=consolidacao.itens_processados,
                status="processado",
                data_processamento=datetime.utcnow()
            )

            # 1️⃣2️⃣ Registrar KPIs
            KPICalculator().registrar_kpis(
                processamento_id=processamento_id,
                emitente_cnpj=cnpj_emitente,
                kpis=kpis
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
                kpis=kpis,
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
                kpis=KPIsRelatorio(),
                erros=erros_processamento,
                data_processamento=datetime.utcnow().isoformat()
            )
