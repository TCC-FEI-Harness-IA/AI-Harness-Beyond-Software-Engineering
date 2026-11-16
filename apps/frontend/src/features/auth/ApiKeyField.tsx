import { Field } from '@/components/primitives/Field'
import { TextInput } from '@/components/primitives/TextInput'

export interface ApiKeyFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  hint?: string
}

/**
 * Campo da chave OpenRouter. Mascarado, sem preenchimento automático e sem sugestões; o valor vive
 * só no estado do formulário até o envio e é apagado logo depois.
 */
export function ApiKeyField({ label, value, onChange, hint }: ApiKeyFieldProps): JSX.Element {
  return (
    <Field
      label={label}
      hint={
        hint ??
        'A chave é validada com a OpenRouter e guardada cifrada num cookie HttpOnly deste navegador — nunca no servidor.'
      }
    >
      <TextInput
        type="password"
        autoComplete="off"
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </Field>
  )
}
