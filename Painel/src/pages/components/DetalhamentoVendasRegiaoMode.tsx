import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  getRegionByUf,
  hierarchyLabelClass,
  type RegionState,
} from '@/pages/components/detalhamentoVendasHelpers';
import { formatCurrency } from '@/services/utils';

type Props = {
  regionHierarchy: RegionState[];
  openRegionStateValues: string[];
  onOpenRegionStateValuesChange: (values: string[]) => void;
  openRegionCityValues: string[];
  onOpenRegionCityValuesChange: (values: string[]) => void;
  openRegionClientValues: string[];
  onOpenRegionClientValuesChange: (values: string[]) => void;
};

export function DetalhamentoVendasRegiaoMode({
  regionHierarchy,
  openRegionStateValues,
  onOpenRegionStateValuesChange,
  openRegionCityValues,
  onOpenRegionCityValuesChange,
  openRegionClientValues,
  onOpenRegionClientValuesChange,
}: Props) {
  return (
    <Accordion
      type="multiple"
      value={openRegionStateValues}
      onValueChange={onOpenRegionStateValuesChange}
      className="w-full"
    >
      {regionHierarchy.map((stateEntry) => (
        <AccordionItem key={stateEntry.key} value={stateEntry.key} className="border-b border-slate-800/80">
          <AccordionTrigger className="px-6 py-5 hover:no-underline">
            <div className="grid w-full gap-3 text-left md:grid-cols-4 md:items-center">
              <div>
                <p className={hierarchyLabelClass}>Estado</p>
                <p className="text-base font-semibold text-white">{stateEntry.uf}</p>
              </div>
              <div>
                <p className={hierarchyLabelClass}>Regiao</p>
                <p className="text-sm text-slate-300">{getRegionByUf(stateEntry.uf)}</p>
              </div>
              <div>
                <p className={hierarchyLabelClass}>Cidades</p>
                <p className="text-sm text-slate-300">{stateEntry.cities.length}</p>
              </div>
              <div>
                <p className={hierarchyLabelClass}>Valor total</p>
                <p className="text-base font-semibold text-white">{formatCurrency(stateEntry.total)}</p>
              </div>
            </div>
          </AccordionTrigger>

          <AccordionContent className="px-6 pb-6">
            <Accordion
              type="multiple"
              value={openRegionCityValues}
              onValueChange={onOpenRegionCityValuesChange}
              className="w-full"
            >
              {stateEntry.cities.map((cityEntry) => (
                <AccordionItem
                  key={cityEntry.key}
                  value={cityEntry.key}
                  className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/75 px-4"
                >
                  <AccordionTrigger className="py-4 hover:no-underline">
                    <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-4">
                      <div>
                        <p className={hierarchyLabelClass}>Cidade</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">{cityEntry.city}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>UF</p>
                        <p className="mt-1 text-sm text-slate-300">{stateEntry.uf}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Clientes</p>
                        <p className="mt-1 text-sm text-slate-300">{cityEntry.clients.length}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Valor total</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(cityEntry.total)}</p>
                      </div>
                    </div>
                  </AccordionTrigger>

                  <AccordionContent className="pb-4">
                    <Accordion
                      type="multiple"
                      value={openRegionClientValues}
                      onValueChange={onOpenRegionClientValuesChange}
                      className="w-full"
                    >
                      {cityEntry.clients.map((clientEntry) => (
                        <AccordionItem
                          key={clientEntry.key}
                          value={clientEntry.key}
                          className="mt-3 rounded-2xl border border-slate-800 bg-slate-950/80 px-4"
                        >
                          <AccordionTrigger className="py-4 hover:no-underline">
                            <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-[minmax(0,1.1fr)_160px_160px_180px] md:items-start">
                              <div className="min-w-0">
                                <p className={hierarchyLabelClass}>Cliente</p>
                                <p className="mt-1 whitespace-normal break-words text-sm font-medium leading-relaxed text-slate-100">
                                  {clientEntry.name}
                                </p>
                                <p className="mt-1 text-xs text-slate-400">{clientEntry.document}</p>
                              </div>
                              <div>
                                <p className={hierarchyLabelClass}>Notas</p>
                                <p className="mt-1 text-sm text-slate-300">{clientEntry.noteCount}</p>
                              </div>
                              <div>
                                <p className={hierarchyLabelClass}>Produtos</p>
                                <p className="mt-1 text-sm text-slate-300">{clientEntry.products.length}</p>
                              </div>
                              <div>
                                <p className={hierarchyLabelClass}>Valor total</p>
                                <p className="mt-1 text-sm font-medium text-slate-100">
                                  {formatCurrency(clientEntry.total)}
                                </p>
                              </div>
                            </div>
                          </AccordionTrigger>

                          <AccordionContent className="pb-4">
                            <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/85">
                              <Table>
                                <TableHeader>
                                  <TableRow className="border-slate-800 bg-slate-950/80 hover:bg-slate-950/80">
                                    <TableHead className="text-slate-300">Cod do produto</TableHead>
                                    <TableHead className="text-slate-300">Nome do produto</TableHead>
                                    <TableHead className="text-slate-300">Notas</TableHead>
                                    <TableHead className="text-slate-300">QTD vendida</TableHead>
                                    <TableHead className="text-right text-slate-300">Valor total</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {clientEntry.products.map((productEntry) => (
                                    <TableRow key={productEntry.key} className="border-slate-800 hover:bg-slate-800/55">
                                      <TableCell className="font-medium text-slate-100">{productEntry.code}</TableCell>
                                      <TableCell className="text-slate-200">{productEntry.description}</TableCell>
                                      <TableCell className="text-slate-300">{productEntry.notesCount}</TableCell>
                                      <TableCell className="text-slate-300">{productEntry.totalQuantity.toFixed(2)}</TableCell>
                                      <TableCell className="text-right font-medium text-slate-100">
                                        {formatCurrency(productEntry.totalValue)}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      ))}
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
