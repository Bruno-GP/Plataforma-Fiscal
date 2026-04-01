import { useMemo } from 'react';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { getNcmDescription, hierarchyLabelClass } from '@/pages/components/detalhamentoVendasHelpers';
import type { NfeNotaDetalhada } from '@/services/nfe';
import { parseDecimal } from '@/services/nfe';
import { formatCurrency } from '@/services/utils';

type Props = {
  notas: NfeNotaDetalhada[];
  openNoteValues: string[];
  onOpenNoteValuesChange: (values: string[]) => void;
  openSupplierValues: string[];
  onOpenSupplierValuesChange: (values: string[]) => void;
  openNcmValues: string[];
  onOpenNcmValuesChange: (values: string[]) => void;
};

type CompraProduto = {
  key: string;
  codigo: string;
  descricao: string;
  quantidade: number;
  valorTotal: number;
  notasCount: number;
};

type CompraNcm = {
  key: string;
  ncm: string;
  descricaoNcm: string;
  valorTotal: number;
  produtos: CompraProduto[];
};

type CompraFornecedor = {
  key: string;
  cnpj: string;
  empresaCompradora: string;
  valorTotal: number;
  notasCount: number;
  ncms: CompraNcm[];
};

export function DetalhamentoComprasNotaMode({
  notas,
  openNoteValues,
  onOpenNoteValuesChange,
  openSupplierValues,
  onOpenSupplierValuesChange,
  openNcmValues,
  onOpenNcmValuesChange,
}: Props) {
  const fornecedores = useMemo<CompraFornecedor[]>(() => {
    const fornecedoresMap = new Map<string, CompraFornecedor>();

    for (const nota of notas) {
      const fornecedorCnpj = (nota.emitente_cnpj || 'Fornecedor nao identificado').trim() || 'Fornecedor nao identificado';
      const empresaCompradora =
        (nota.destinatario_nome || nota.destinatario_documento || 'Empresa nao identificada').trim() ||
        'Empresa nao identificada';
      const fornecedorKey = `fornecedor-${fornecedorCnpj}`;
      const valorNota = parseDecimal(nota.valor_total_nf);

      let fornecedor = fornecedoresMap.get(fornecedorKey);
      if (!fornecedor) {
        fornecedor = {
          key: fornecedorKey,
          cnpj: fornecedorCnpj,
          empresaCompradora,
          valorTotal: 0,
          notasCount: 0,
          ncms: [],
        };
        fornecedoresMap.set(fornecedorKey, fornecedor);
      }

      fornecedor.valorTotal += valorNota;
      fornecedor.notasCount += 1;

      for (const item of nota.itens) {
        const ncm = (item.ncm || 'sem-ncm').trim() || 'sem-ncm';
        const ncmKey = `${fornecedorKey}-ncm-${ncm}`;
        const valorItem = parseDecimal(item.valor_total);
        const quantidade = parseDecimal(item.quantidade);
        const descricaoProduto = (item.descricao || 'Produto nao identificado').trim() || 'Produto nao identificado';
        const codigoProduto = (item.produto_codigo || '-').trim() || '-';
        const descricaoNcm = getNcmDescription(item.descricao_ncm);

        let ncmGroup = fornecedor.ncms.find((entry) => entry.key === ncmKey);
        if (!ncmGroup) {
          ncmGroup = {
            key: ncmKey,
            ncm,
            descricaoNcm,
            valorTotal: 0,
            produtos: [],
          };
          fornecedor.ncms.push(ncmGroup);
        }

        ncmGroup.valorTotal += valorItem;

        const produtoKey = `${ncmKey}-produto-${codigoProduto}-${descricaoProduto.toLowerCase()}`;
        let produto = ncmGroup.produtos.find((entry) => entry.key === produtoKey);
        if (!produto) {
          produto = {
            key: produtoKey,
            codigo: codigoProduto,
            descricao: descricaoProduto,
            quantidade: 0,
            valorTotal: 0,
            notasCount: 0,
          };
          ncmGroup.produtos.push(produto);
        }

        produto.quantidade += quantidade;
        produto.valorTotal += valorItem;
        produto.notasCount += 1;
      }
    }

    return Array.from(fornecedoresMap.values())
      .map((fornecedor) => ({
        ...fornecedor,
        ncms: fornecedor.ncms
          .map((ncm) => ({
            ...ncm,
            produtos: [...ncm.produtos].sort((a, b) => b.valorTotal - a.valorTotal),
          }))
          .sort((a, b) => b.valorTotal - a.valorTotal),
      }))
      .sort((a, b) => b.valorTotal - a.valorTotal);
  }, [notas]);

  return (
    <Accordion type="multiple" value={openNoteValues} onValueChange={onOpenNoteValuesChange} className="w-full">
      {fornecedores.map((fornecedor) => (
        <AccordionItem key={fornecedor.key} value={fornecedor.key} className="border-b border-slate-800/80">
          <AccordionTrigger className="px-6 py-5 hover:no-underline">
            <div className="grid w-full gap-3 text-left md:grid-cols-[1fr_1fr] md:items-center">
              <div>
                <p className={hierarchyLabelClass}>Fornecedor</p>
                <p className="text-base font-semibold text-white">{fornecedor.cnpj}</p>
              </div>
              <div>
                <p className={hierarchyLabelClass}>Valor total comprado</p>
                <p className="text-base font-semibold text-white">{formatCurrency(fornecedor.valorTotal)}</p>
              </div>
            </div>
          </AccordionTrigger>

          <AccordionContent className="px-6 pb-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/75 px-4 py-4">
              <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-3">
                <div>
                  <p className={hierarchyLabelClass}>CNPJ do fornecedor</p>
                  <p className="mt-1 text-sm font-medium text-slate-100">{fornecedor.cnpj}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Empresa compradora</p>
                  <p className="mt-1 text-sm text-slate-300">{fornecedor.empresaCompradora}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>Documentos no periodo</p>
                  <p className="mt-1 text-sm text-slate-300">{fornecedor.notasCount}</p>
                </div>
              </div>
            </div>

            <Accordion
              type="multiple"
              value={openSupplierValues}
              onValueChange={onOpenSupplierValuesChange}
              className="mt-3 w-full"
            >
              {fornecedor.ncms.map((group) => (
                <AccordionItem
                  key={group.key}
                  value={group.key}
                  className="mt-3 rounded-2xl border border-slate-800 bg-slate-950/80 px-4"
                >
                  <AccordionTrigger className="py-4 hover:no-underline">
                    <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-[minmax(0,1fr)_220px] md:items-start">
                      <div className="min-w-0">
                        <p className={hierarchyLabelClass}>NCM</p>
                        <p className="mt-1 whitespace-normal break-words pr-4 text-sm font-medium leading-relaxed text-slate-100">
                          {group.ncm} - {group.descricaoNcm}
                        </p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Valor total</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(group.valorTotal)}</p>
                      </div>
                    </div>
                  </AccordionTrigger>

                  <AccordionContent className="pb-4">
                    <Accordion type="multiple" value={openNcmValues} onValueChange={onOpenNcmValuesChange} className="w-full">
                      <AccordionItem value={`${group.key}-produtos`} className="rounded-2xl border border-slate-800 bg-slate-900/85 px-4">
                        <AccordionTrigger className="py-4 hover:no-underline">
                          <div className="text-left">
                            <p className={hierarchyLabelClass}>Produto</p>
                            <p className="mt-1 text-sm font-medium text-slate-100">Abrir visualizacao detalhada</p>
                          </div>
                        </AccordionTrigger>

                        <AccordionContent className="pb-2">
                          <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/85">
                            <Table className="min-w-[760px]">
                              <TableHeader>
                                <TableRow className="border-slate-800 bg-slate-950/80 hover:bg-slate-950/80">
                                  <TableHead className="text-slate-300">Cod do produto</TableHead>
                                  <TableHead className="text-slate-300">Nome do produto</TableHead>
                                  <TableHead className="text-slate-300">QTD comprada</TableHead>
                                  <TableHead className="text-right text-slate-300">Valor total</TableHead>
                                  <TableHead className="text-right text-slate-300">Documentos</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {group.produtos.map((item) => (
                                  <TableRow key={item.key} className="border-slate-800 hover:bg-slate-800/55">
                                    <TableCell className="font-medium text-slate-100">{item.codigo}</TableCell>
                                    <TableCell className="text-slate-200">{item.descricao}</TableCell>
                                    <TableCell className="text-slate-300">{item.quantidade.toFixed(2)}</TableCell>
                                    <TableCell className="text-right font-medium text-slate-100">{formatCurrency(item.valorTotal)}</TableCell>
                                    <TableCell className="text-right text-slate-300">{item.notasCount}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
