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

class ProcessarNFeService:
    def executar(self, request: ProcessarNFeRequest) -> ProcessarNFeResponse:
        cnpj_emitente = ""
        periodo_ano = 0
        periodo_mes = 0
        periodos_encontrados = []

        try:
            # 1️⃣ Ler XMLs
            xmls = XmlReader().ler_pasta(request.pasta_xml)
            if not xmls:
                raise Exception("Nenhum XML válido encontrado")

            # 2️⃣ Extrair notas
            notas = NFeExtractor().extrair(xmls)
            if not notas:
                raise Exception("Nenhuma NFe válida extraída")

            # 3️⃣ Determinar períodos a partir das datas de emissão
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
            else:
                print(
                    "[AVISO] XMLs contêm mais de um período:",
                    periodos_encontrados
                )

            # 4️⃣ Identificar CNPJ emitente
            cnpjs = {n.emitente_cnpj for n in notas}
            if len(cnpjs) != 1:
                raise Exception("Mais de um CNPJ de emitente encontrado")

            cnpj_emitente = cnpjs.pop()
            print(f"[INFO] CNPJ identificado: {cnpj_emitente}")

            # 5️⃣ Consolidar notas e itens
            consolidacao = NFeConsolidator().consolidar(notas)
            print(f"[INFO] Notas processadas: {consolidacao.notas_processadas}")
            print(f"[INFO] Itens processados: {consolidacao.itens_processados}")

            # 6️⃣ Calcular KPIs
            kpis = KPICalculator().calcular(consolidacao.notas)

            # 7️⃣ Retorno final (sucesso)
            return ProcessarNFeResponse(
                status="processado",
                cnpj_emitente=cnpj_emitente,
                periodo_ano=periodo_ano,
                periodo_mes=periodo_mes,
                periodos_encontrados=periodos_encontrados,
                notas_processadas=consolidacao.notas_processadas,
                itens_processados=consolidacao.itens_processados,
                kpis=kpis,
                erros=[],
                data_processamento=datetime.utcnow().isoformat()
            )

        except Exception as exc:
            print(f"[ERRO NO PROCESSAMENTO] {exc}")

            return ProcessarNFeResponse(
                status="erro",
                cnpj_emitente=cnpj_emitente,
                periodo_ano=periodo_ano,
                periodo_mes=periodo_mes,
                periodos_encontrados=periodos_encontrados,
                notas_processadas=0,
                itens_processados=0,
                kpis=KPIsRelatorio(),
                erros=[
                    ErroProcessamento(
                        codigo="PROCESSAMENTO_NFE_ERRO",
                        mensagem=str(exc)
                    ).model_dump()
                ],
                data_processamento=datetime.utcnow().isoformat()
            )