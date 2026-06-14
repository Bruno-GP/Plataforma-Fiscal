import { useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';

import type { CatalogoComboboxProps } from '../types';

export function CatalogoCombobox<TItem>({
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
}: CatalogoComboboxProps<TItem>) {
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
