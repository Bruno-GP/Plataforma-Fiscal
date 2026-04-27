import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  getNcmDescription,
  getRegionByUf,
  hierarchyLabelClass,
} from '@/pages/components/detalhamentoVendasHelpers';
import type { NfeNotaDetalhada } from '@/services/nfe';
import { parseDecimal } from '@/services/nfe';
import { formatCurrency } from '@/services/utils';

type Props = {
  notas: NfeNotaDetalhada[];
  openNoteValues: string[];
  onOpenNoteValuesChange: (values: string[]) => void;
  openNoteClientValues: string[];
  onOpenNoteClientValuesChange: (values: string[]) => void;
  openNcmValues: string[];
  onOpenNcmValuesChange: (values: string[]) => void;
};

export function DetalhamentoVendasNotaMode({
  notas,
  openNoteValues,
  onOpenNoteValuesChange,
  openNoteClientValues,
  onOpenNoteClientValuesChange,
  openNcmValues,
  onOpenNcmValuesChange,
}: Props) {
  return (
    <Accordion type="multiple" value={openNoteValues} onValueChange={onOpenNoteValuesChange} className="w-full">
      {notas.map((nota) => {
        const notaValue = `${nota.numero_nf}-${nota.data_emissao}`;
        const clientValue = `cliente-${nota.numero_nf}-${nota.data_emissao}`;
        const isNfse = (nota.modelo || '').trim().toUpperCase() === 'NFSE';
        const noteTotal = parseDecimal(nota.valor_total_nf);
        const itemBaseTotal = nota.itens.reduce((total, item) => total + parseDecimal(item.valor_total), 0);

        const ncmGroups = Array.from(
          nota.itens.reduce((map, item) => {
            const key = item.ncm || 'sem-ncm';
            const current = map.get(key) ?? { ncm: item.ncm || '-', descricaoNcm: '', total: 0 };
            const descricaoNcm = getNcmDescription(item.descricao_ncm);
            if (descricaoNcm.length > current.descricaoNcm.length) current.descricaoNcm = descricaoNcm;
            current.total += parseDecimal(item.valor_total);
            map.set(key, current);
            return map;
          }, new Map<string, { ncm: string; descricaoNcm: string; total: number }>()),
        ).map(([, value]) => value);

        return (
          <AccordionItem key={notaValue} value={notaValue} className="border-b border-slate-800/80">
            <AccordionTrigger className="px-6 py-5 hover:no-underline">
              <div className="grid w-full gap-3 text-left md:grid-cols-[1fr_1fr] md:items-center">
                <div>
                  <p className={hierarchyLabelClass}>Nota</p>
                  <p className="text-base font-semibold text-white">{nota.numero_nf}</p>
                </div>
                <div>
                  <p className={hierarchyLabelClass}>{isNfse ? 'Valor liquido da nota' : 'Valor total da nota'}</p>
                  <p className="text-base font-semibold text-white">{formatCurrency(noteTotal)}</p>
                </div>
              </div>
            </AccordionTrigger>

            <AccordionContent className="px-6 pb-6">
              <Accordion
                type="multiple"
                value={openNoteClientValues}
                onValueChange={onOpenNoteClientValuesChange}
                className="w-full"
              >
                <AccordionItem value={clientValue} className="rounded-2xl border border-slate-800 bg-slate-900/75 px-4">
                  <AccordionTrigger className="py-4 hover:no-underline">
                    <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-4">
                      <div>
                        <p className={hierarchyLabelClass}>Nome do cliente</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">
                          {nota.destinatario_nome || 'Cliente nao identificado'}
                        </p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>CPF/CNPJ</p>
                        <p className="mt-1 text-sm text-slate-300">{nota.destinatario_documento || 'Nao informado'}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Regiao</p>
                        <p className="mt-1 text-sm text-slate-300">{getRegionByUf(nota.destinatario_uf || '')}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Cidade</p>
                        <p className="mt-1 text-sm text-slate-300">
                          {nota.destinatario_cidade || 'Nao informada'}
                          {nota.destinatario_uf ? ` - ${nota.destinatario_uf}` : ''}
                        </p>
                      </div>
                    </div>
                  </AccordionTrigger>

                  <AccordionContent className="pb-4">
                    <Accordion type="multiple" value={openNcmValues} onValueChange={onOpenNcmValuesChange} className="w-full">
                      {ncmGroups.map((group) => (
                        <AccordionItem
                          key={`ncm-${nota.numero_nf}-${nota.data_emissao}-${group.ncm}`}
                          value={`ncm-${nota.numero_nf}-${nota.data_emissao}-${group.ncm}`}
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
                                <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(group.total)}</p>
                              </div>
                            </div>
                          </AccordionTrigger>

                          <AccordionContent className="pb-4">
                            <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/85">
                              <Table className="min-w-[920px]">
                                <TableHeader>
                                  <TableRow className="border-slate-800 bg-slate-950/80 hover:bg-slate-950/80">
                                    <TableHead className="text-slate-300">Cod do produto</TableHead>
                                    <TableHead className="text-slate-300">Nome do produto</TableHead>
                                    <TableHead className="text-slate-300">QTD vendida</TableHead>
                                    <TableHead className="text-right text-slate-300">
                                      {isNfse ? 'Valor liquido' : 'Valor total'}
                                    </TableHead>
                                    <TableHead className="text-right text-slate-300">
                                      Tributos
                                    </TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {nota.itens
                                    .filter((item) => (item.ncm || '-') === group.ncm)
                                    .map((item) => {
                                      const itemTotal = parseDecimal(item.valor_total);
                                      const proportion = itemBaseTotal > 0 ? itemTotal / itemBaseTotal : 0;
                                      const tributos = item.tributos ?? [];
                                      const tributosLegados = [
                                        { codigo: isNfse ? 'Retencoes' : 'ICMS', valor: parseDecimal(nota.valor_icms) * proportion },
                                        { codigo: 'IPI', valor: parseDecimal(nota.valor_ipi) * proportion },
                                        { codigo: 'PIS', valor: parseDecimal(nota.valor_pis) * proportion },
                                        { codigo: 'COFINS', valor: parseDecimal(nota.valor_cofins) * proportion },
                                      ].filter((tributo) => isNfse ? tributo.codigo === 'Retencoes' : tributo.valor !== 0);

                                      return (
                                        <TableRow
                                          key={`${nota.numero_nf}-${group.ncm}-${item.item_numero}`}
                                          className="border-slate-800 hover:bg-slate-800/55"
                                        >
                                          <TableCell className="font-medium text-slate-100">{item.produto_codigo || '-'}</TableCell>
                                          <TableCell className="text-slate-200">{item.descricao || 'Produto nao identificado'}</TableCell>
                                          <TableCell className="text-slate-300">{parseDecimal(item.quantidade).toFixed(2)}</TableCell>
                                          <TableCell className="text-right font-medium text-slate-100">{formatCurrency(itemTotal)}</TableCell>
                                          <TableCell className="min-w-[280px] text-right">
                                            {tributos.length > 0 ? (
                                              <div className="flex flex-wrap justify-end gap-2">
                                                {tributos.map((tributo) => {
                                                  const valor = parseDecimal(tributo.valor_tributo);
                                                  const natureza = tributo.natureza === 'credito' ? 'Credito' : 'Debito';
                                                  return (
                                                    <Badge
                                                      key={`${item.id}-${tributo.tributo_codigo}-${natureza}`}
                                                      variant="outline"
                                                      className="border-slate-700 bg-slate-950/70 text-slate-200"
                                                    >
                                                      {tributo.tributo_codigo} {formatCurrency(valor)} - {natureza}
                                                    </Badge>
                                                  );
                                                })}
                                              </div>
                                            ) : (
                                              <div className="flex flex-wrap justify-end gap-2">
                                                {tributosLegados.length > 0 ? (
                                                  tributosLegados.map((tributo) => (
                                                    <Badge
                                                      key={`${item.item_numero}-${tributo.codigo}`}
                                                      variant="outline"
                                                      className="border-slate-800 bg-slate-950/60 text-slate-400"
                                                    >
                                                      {tributo.codigo} {formatCurrency(tributo.valor)}
                                                    </Badge>
                                                  ))
                                                ) : (
                                                  <span className="text-slate-500">Sem tributos</span>
                                                )}
                                              </div>
                                            )}
                                          </TableCell>
                                        </TableRow>
                                      );
                                    })}
                                </TableBody>
                              </Table>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      ))}
                    </Accordion>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </AccordionContent>
          </AccordionItem>
        );
      })}
    </Accordion>
  );
}
