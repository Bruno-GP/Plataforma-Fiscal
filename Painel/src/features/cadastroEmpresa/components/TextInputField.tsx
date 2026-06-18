import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import type { TextInputFieldProps } from '../types';

export function TextInputField({
  id,
  label,
  type,
  placeholder,
  value,
  onChange,
  inputMode,
  maxLength,
  minLength,
}: TextInputFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        inputMode={inputMode}
        maxLength={maxLength}
        minLength={minLength}
        required
      />
    </div>
  );
}
