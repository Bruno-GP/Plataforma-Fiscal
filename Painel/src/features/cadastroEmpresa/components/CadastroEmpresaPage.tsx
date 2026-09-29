import { Loader2 } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { CatalogoCombobox } from './CatalogoCombobox';
import { TextInputField } from './TextInputField';
import { getCidadeEmptyMessage } from '../helpers/cidadeMessages';
import { useCadastroEmpresaPageData } from '../hooks/useCadastroEmpresaPageData';

export function CadastroEmpresaPage() {
  const {
    empresaNome,
    setEmpresaNome,
    email,
    setEmail,
    password,
    setPassword,
    cnpj,
    origemFiscal,
    setOrigemFiscal,
    ufSearch,
    setUfSearch,
    cidadeSearch,
    setCidadeSearch,
    selectedUf,
    selectedCidade,
    formError,
    isLoading,
    ufsQuery,
    cidadesQuery,
    handleUfSelect,
    handleCidadeSelect,
    handleSubmit,
    cnaeFiscal,
    cnaeFiscalDescricao,
    isBuscandoCnpj,
    handleBuscarCnpj,
    handleCnpjChange,
  } = useCadastroEmpresaPageData();

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
              <Label htmlFor="cnpj">CNPJ</Label>
              <div className="flex gap-2">
                <Input
                  id="cnpj"
                  type="text"
                  placeholder="00.000.000/0000-00"
                  value={cnpj}
                  onChange={(e) => handleCnpjChange(e.target.value)}
                  inputMode="numeric"
                  maxLength={18}
                  required
                />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleBuscarCnpj}
                  disabled={isBuscandoCnpj}
                >
                  {isBuscandoCnpj ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Buscar'}
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="cnae">CNAE</Label>
              <Input
                id="cnae"
                type="text"
                placeholder="Preenchido ao buscar o CNPJ"
                value={cnaeFiscal ? `${cnaeFiscal}${cnaeFiscalDescricao ? ` - ${cnaeFiscalDescricao}` : ''}` : ''}
                disabled
                readOnly
              />
            </div>
            <TextInputField
              id="empresaNome"
              label="Nome da empresa"
              type="text"
              placeholder="Preenchido ao buscar o CNPJ"
              value={empresaNome}
              onChange={(e) => setEmpresaNome(e.target.value)}
              disabled
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <CatalogoCombobox
                label="UF da empresa"
                placeholder="Preenchido ao buscar o CNPJ"
                searchPlaceholder="Digite para pesquisar a UF"
                emptyMessage={ufsQuery.isLoading ? 'Carregando...' : 'Nenhuma UF encontrada.'}
                disabled
                selectedLabel={selectedUf?.uf ?? ''}
                searchValue={ufSearch}
                onSearchValueChange={setUfSearch}
                onSelectItem={handleUfSelect}
                items={ufsQuery.data ?? []}
                isLoading={ufsQuery.isLoading}
                itemLabel={(item) => item.uf}
                itemDescription={(item) => `${item.quantidade_municipios} municipios`}
              />
              <CatalogoCombobox
                label="Cidade da empresa"
                placeholder="Preenchido ao buscar o CNPJ"
                searchPlaceholder="Digite para pesquisar a cidade"
                emptyMessage={getCidadeEmptyMessage(selectedUf, cidadesQuery.isLoading)}
                disabled
                selectedLabel={selectedCidade?.nome ?? ''}
                searchValue={cidadeSearch}
                onSearchValueChange={setCidadeSearch}
                onSelectItem={handleCidadeSelect}
                items={cidadesQuery.data ?? []}
                isLoading={cidadesQuery.isLoading}
                itemLabel={(item) => item.nome}
                itemDescription={(item) => `${item.uf} \u2022 ${item.codigo_ibge}`}
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
                value={origemFiscal}
                onChange={(e) => setOrigemFiscal(e.target.value as 'xml' | 'sped' | 'conta_azul')}
              >
                <option value="xml">Empresa usa XML</option>
                <option value="sped">Empresa usa SPED Fiscal</option>
                <option value="conta_azul">Empresa usa Conta Azul</option>
              </select>
            </div>
            <TextInputField
              id="email"
              label="Email do login"
              type="email"
              placeholder="acesso@empresa.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextInputField
              id="password"
              label="Senha"
              type="password"
              placeholder="********"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={12}
            />
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
