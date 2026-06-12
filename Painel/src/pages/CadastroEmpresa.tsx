import { useDeferredValue, useState } from 'react';
import { Check, ChevronDown, Loader2 } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  fetchMunicipiosPorUf,
  fetchUfsCatalogo,
  type MunicipioCatalogoItem,
  type UFCatalogoItem,
} from '@/services/municipios';

type CatalogoItem = UFCatalogoItem | MunicipioCatalogoItem;

interface CatalogoComboboxProps {
  label: string;
  placeholder: string;
  searchPlaceholder: string;
  emptyMessage: string;
  disabled?: boolean;
  selectedLabel: string;
  searchValue: string;
  onSearchValueChange: (value: string) => void;
  onSelectItem: (item: CatalogoItem) => void;
  items: CatalogoItem[];
  isLoading: boolean;
  itemLabel: (item: CatalogoItem) => string;
  itemDescription?: (item: CatalogoItem) => string;
}

function CatalogoCombobox({
  label,
  placeholder,
  searchPlaceholder,
  emptyMessage,
  disabled = false,
  selectedLabel,
  searchValue,
  onSearchValueChange,
  onSelectItem,
  items,
  isLoading,
  itemLabel,
  itemDescription,
}: CatalogoComboboxProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-label={label}
            aria-expanded={open}
            className={cn(
              'h-10 w-full justify-between bg-background font-normal',
              !selectedLabel && 'text-muted-foreground',
            )}
            disabled={disabled}
          >
            <span className="truncate text-left">{selectedLabel || placeholder}</span>
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-[var(--radix-popover-trigger-width)] overflow-hidden border-slate-800 bg-slate-950 p-0 text-slate-50 shadow-2xl"
          align="start"
        >
          <Command className="bg-slate-950 text-slate-50">
            <CommandInput
              placeholder={searchPlaceholder}
              value={searchValue}
              onValueChange={onSearchValueChange}
              className="border-slate-800 bg-slate-950 text-slate-50 placeholder:text-slate-400"
            />
            <CommandList>
              {isLoading ? (
                <div className="p-3 text-sm text-slate-400">Carregando...</div>
              ) : items.length ? (
                <CommandGroup>
                  {items.map((item) => {
                    const labelItem = itemLabel(item);
                    const description = itemDescription?.(item);

                    return (
                      <CommandItem
                        key={labelItem}
                        value={labelItem}
                        className="data-[selected=true]:bg-slate-800 data-[selected=true]:text-slate-50"
                        onSelect={() => {
                          onSelectItem(item);
                          setOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            'mr-2 h-4 w-4',
                            selectedLabel === labelItem ? 'opacity-100' : 'opacity-0',
                          )}
                        />
                        <div className="flex min-w-0 flex-1 flex-col">
                          <span className="truncate">{labelItem}</span>
                          {description ? (
                            <span className="truncate text-xs text-muted-foreground">{description}</span>
                          ) : null}
                        </div>
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
              ) : (
                <CommandEmpty className="text-slate-400">{emptyMessage}</CommandEmpty>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export default function CadastroEmpresaInterno() {
  const [empresaNome, setEmpresaNome] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [temSped, setTemSped] = useState(false);
  const [ufSearch, setUfSearch] = useState('');
  const [cidadeSearch, setCidadeSearch] = useState('');
  const [selectedUf, setSelectedUf] = useState<UFCatalogoItem | null>(null);
  const [selectedCidade, setSelectedCidade] = useState<MunicipioCatalogoItem | null>(null);
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const deferredUfSearch = useDeferredValue(ufSearch);
  const deferredCidadeSearch = useDeferredValue(cidadeSearch);

  const ufsQuery = useQuery({
    queryKey: ['municipios-ufs', deferredUfSearch],
    queryFn: () => fetchUfsCatalogo(deferredUfSearch),
  });

  const cidadesQuery = useQuery({
    queryKey: ['municipios-cidades', selectedUf?.uf ?? '', deferredCidadeSearch],
    queryFn: () => fetchMunicipiosPorUf(selectedUf?.uf ?? '', deferredCidadeSearch),
    enabled: Boolean(selectedUf?.uf),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedUf?.uf) {
      setFormError('Selecione uma UF antes de cadastrar a empresa.');
      return;
    }

    if (!selectedCidade) {
      setFormError('Selecione uma cidade vinculada ao catalogo de municipios.');
      return;
    }

    if (!selectedCidade.municipio_id || !selectedCidade.codigo_ibge) {
      setFormError('A cidade selecionada precisa ter municipio_id e codigo_ibge validos.');
      return;
    }

    setFormError('');
    setIsLoading(true);

    try {
      const result = await register(
        empresaNome,
        email,
        password,
        cnpj,
        temSped,
        false,
        selectedUf.uf,
        selectedCidade.nome,
        selectedCidade.municipio_id,
        selectedCidade.codigo_ibge,
      );

      if (result.ok) {
        toast({
          title: 'Cadastro realizado!',
          description: 'Empresa e login cadastrados com sucesso. Redirecionando para o login...',
        });
        navigate('/login', { replace: true });
        return;
      }

      const errorMessage = result.message ?? 'Nao foi possivel cadastrar.';
      toast({
        variant: 'destructive',
        title: 'Erro no cadastro',
        description: errorMessage,
      });
      setFormError(errorMessage);
    } catch {
      const errorMessage = 'Ocorreu um erro ao cadastrar empresa e login.';
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: errorMessage,
      });
      setFormError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Cadastro interno</CardTitle>
          <CardDescription>
            Uso exclusivo da equipe interna para cadastrar empresa e primeiro acesso.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="empresaNome">Nome da empresa</Label>
              <Input
                id="empresaNome"
                type="text"
                placeholder="Empresa Exemplo LTDA"
                value={empresaNome}
                onChange={(e) => setEmpresaNome(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cnpj">CNPJ</Label>
              <Input
                id="cnpj"
                type="text"
                placeholder="00.000.000/0000-00"
                value={cnpj}
                onChange={(e) => setCnpj(e.target.value)}
                inputMode="numeric"
                maxLength={18}
                required
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <CatalogoCombobox
                label="UF da empresa"
                placeholder="Pesquisar UF"
                searchPlaceholder="Digite para pesquisar a UF"
                emptyMessage={ufsQuery.isLoading ? 'Carregando...' : 'Nenhuma UF encontrada.'}
                selectedLabel={selectedUf?.uf ?? ''}
                searchValue={ufSearch}
                onSearchValueChange={setUfSearch}
                onSelectItem={(item) => {
                  const ufItem = item as UFCatalogoItem;
                  setSelectedUf(ufItem);
                  setUfSearch('');
                  setSelectedCidade(null);
                  setCidadeSearch('');
                  setFormError('');
                }}
                items={(ufsQuery.data ?? []) as CatalogoItem[]}
                isLoading={ufsQuery.isLoading}
                itemLabel={(item) => (item as UFCatalogoItem).uf}
                itemDescription={(item) => `${(item as UFCatalogoItem).quantidade_municipios} municipios`}
              />
              <CatalogoCombobox
                label="Cidade da empresa"
                placeholder={selectedUf ? 'Pesquisar cidade' : 'Selecione a UF primeiro'}
                searchPlaceholder="Digite para pesquisar a cidade"
                emptyMessage={
                  selectedUf
                    ? cidadesQuery.isLoading
                      ? 'Carregando...'
                      : 'Nenhuma cidade encontrada.'
                    : 'Selecione uma UF valida para listar cidades.'
                }
                disabled={!selectedUf}
                selectedLabel={selectedCidade?.nome ?? ''}
                searchValue={cidadeSearch}
                onSearchValueChange={setCidadeSearch}
                onSelectItem={(item) => {
                  const cidadeItem = item as MunicipioCatalogoItem;
                  setSelectedCidade(cidadeItem);
                  setCidadeSearch('');
                  setFormError('');
                }}
                items={(cidadesQuery.data ?? []) as CatalogoItem[]}
                isLoading={cidadesQuery.isLoading}
                itemLabel={(item) => (item as MunicipioCatalogoItem).nome}
                itemDescription={(item) => `${(item as MunicipioCatalogoItem).uf} • ${(item as MunicipioCatalogoItem).codigo_ibge}`}
              />
            </div>
            {formError ? (
              <Alert variant="destructive">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="temSped">Origem fiscal</Label>
              <select
                id="temSped"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={temSped ? 'sped' : 'xml'}
                onChange={(e) => setTemSped(e.target.value === 'sped')}
              >
                <option value="xml">Empresa usa XML</option>
                <option value="sped">Empresa usa SPED Fiscal</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email do login</Label>
              <Input
                id="email"
                type="email"
                placeholder="acesso@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                type="password"
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={12}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Cadastrar empresa
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
