import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { getRegionByUf, hierarchyLabelClass } from '@/pages/components/detalhamentoVendasHelpers';
import { formatCurrency } from '@/services/utils';

type FiscalHierarchyProduct = {
  key: string;
  code: string;
  description: string;
  totalValue: number;
  taxValue: number;
  taxPercent: number;
};

type FiscalHierarchyNcm = {
  key: string;
  ncm: string;
  description: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  products: FiscalHierarchyProduct[];
};

type FiscalHierarchyCity = {
  key: string;
  city: string;
  uf: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  ncms: FiscalHierarchyNcm[];
};

type FiscalHierarchyState = {
  key: string;
  uf: string;
  total: number;
  taxValue: number;
  taxPercent: number;
  cities: FiscalHierarchyCity[];
};

type Props = {
  hierarchy: FiscalHierarchyState[];
  openStateValues: string[];
  onOpenStateValuesChange: (values: string[]) => void;
  openCityValues: string[];
  onOpenCityValuesChange: (values: string[]) => void;
  openNcmValues: string[];
  onOpenNcmValuesChange: (values: string[]) => void;
};

export function DetalhamentoFiscalHierarquiaMode({
  hierarchy,
  openStateValues,
  onOpenStateValuesChange,
  openCityValues,
  onOpenCityValuesChange,
  openNcmValues,
  onOpenNcmValuesChange,
}: Props) {
  return (
    <Accordion type="multiple" value={openStateValues} onValueChange={onOpenStateValuesChange} className="w-full">
      {hierarchy.map((stateEntry) => (
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
                <p className={hierarchyLabelClass}>Imposto estimado</p>
                <p className="text-sm text-slate-300">{formatCurrency(stateEntry.taxValue)}</p>
              </div>
              <div>
                <p className={hierarchyLabelClass}>Faturamento</p>
                <p className="text-base font-semibold text-white">{formatCurrency(stateEntry.total)}</p>
              </div>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-6">
            <Accordion type="multiple" value={openCityValues} onValueChange={onOpenCityValuesChange} className="w-full">
              {stateEntry.cities.map((cityEntry) => (
                <AccordionItem key={cityEntry.key} value={cityEntry.key} className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/75 px-4">
                  <AccordionTrigger className="py-4 hover:no-underline">
                    <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-4">
                      <div>
                        <p className={hierarchyLabelClass}>Cidade</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">{cityEntry.city}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>NCMs</p>
                        <p className="mt-1 text-sm text-slate-300">{cityEntry.ncms.length}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Imposto estimado</p>
                        <p className="mt-1 text-sm text-slate-300">{formatCurrency(cityEntry.taxValue)}</p>
                      </div>
                      <div>
                        <p className={hierarchyLabelClass}>Faturamento</p>
                        <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(cityEntry.total)}</p>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="pb-4">
                    <Accordion type="multiple" value={openNcmValues} onValueChange={onOpenNcmValuesChange} className="w-full">
                      {cityEntry.ncms.map((ncmEntry) => (
                        <AccordionItem key={ncmEntry.key} value={ncmEntry.key} className="mt-3 rounded-2xl border border-slate-800 bg-slate-950/80 px-4">
                          <AccordionTrigger className="py-4 hover:no-underline">
                            <div className="grid w-full gap-3 pr-4 text-left md:grid-cols-[minmax(0,1.1fr)_160px_180px_180px] md:items-start">
                              <div className="min-w-0">
                                <p className={hierarchyLabelClass}>NCM</p>
                                <p className="mt-1 whitespace-normal break-words text-sm font-medium leading-relaxed text-slate-100">
                                  {ncmEntry.ncm}
                                </p>
                                <p className="mt-1 text-xs text-slate-400">{ncmEntry.description}</p>
                              </div>
                              <div>
                                <p className={hierarchyLabelClass}>Produtos</p>
                                <p className="mt-1 text-sm text-slate-300">{ncmEntry.products.length}</p>
                              </div>
                              <div>
                                <p className={hierarchyLabelClass}>Imposto estimado</p>
                                <p className="mt-1 text-sm text-slate-300">{formatCurrency(ncmEntry.taxValue)}</p>
                              </div>
                              <div>
                                <p className={hierarchyLabelClass}>Faturamento</p>
                                <p className="mt-1 text-sm font-medium text-slate-100">{formatCurrency(ncmEntry.total)}</p>
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
                                    <TableHead className="text-right text-slate-300">Faturamento</TableHead>
                                    <TableHead className="text-right text-slate-300">Imposto (R$)</TableHead>
                                    <TableHead className="text-right text-slate-300">Imposto (%)</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {ncmEntry.products.map((productEntry) => (
                                    <TableRow key={productEntry.key} className="border-slate-800 hover:bg-slate-800/55">
                                      <TableCell className="font-medium text-slate-100">{productEntry.code}</TableCell>
                                      <TableCell className="text-slate-200">{productEntry.description}</TableCell>
                                      <TableCell className="text-right font-medium text-slate-100">{formatCurrency(productEntry.totalValue)}</TableCell>
                                    <TableCell className="text-right text-slate-300">{formatCurrency(productEntry.taxValue)}</TableCell>
                                    <TableCell className="text-right text-slate-300">-</TableCell>
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

export type { FiscalHierarchyState };
