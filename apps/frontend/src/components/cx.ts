// Combina nomes de classe CSS Module, descartando valores falsy — evita template literal
// repetido em todo componente com classe condicional.

export function cx(...classNames: Array<string | false | null | undefined>): string {
  return classNames.filter((name): name is string => Boolean(name)).join(' ')
}
