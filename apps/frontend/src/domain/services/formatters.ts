// Formatação centralizada em pt-BR via Intl (README, seções 9 e 10). Todo número, tempo e
// data exibidos no app passa por aqui — nenhum `toFixed` nem concatenação de string solta em
// componente.

const LOCALE = 'pt-BR'

const tokensFormatter = new Intl.NumberFormat(LOCALE)
const compactTokensFormatter = new Intl.NumberFormat(LOCALE, {
  notation: 'compact',
  maximumFractionDigits: 1,
})
const secondsFormatter = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const dateTimeFormatter = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'short', timeStyle: 'short' })
const relativeTimeFormatter = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' })
const percentFormatter = new Intl.NumberFormat(LOCALE, { style: 'percent', maximumFractionDigits: 1 })
const temperatureFormatter = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export function formatTokens(tokens: number): string {
  return tokensFormatter.format(tokens)
}

export function formatCompactTokens(tokens: number): string {
  return compactTokensFormatter.format(tokens)
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`

  if (ms < 60000) return `${secondsFormatter.format(ms / 1000)} s`

  const totalSeconds = Math.round(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return seconds > 0 ? `${minutes} min ${seconds} s` : `${minutes} min`
}

export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso))
}

// Divisores em segundos, do maior para o menor — cada um usado enquanto a diferença couber
// nele (README, "há 3 minutos" via Intl.RelativeTimeFormat).
const RELATIVE_UNITS: Array<{ unit: Intl.RelativeTimeFormatUnit; seconds: number }> = [
  { unit: 'year', seconds: 365 * 24 * 60 * 60 },
  { unit: 'month', seconds: 30 * 24 * 60 * 60 },
  { unit: 'day', seconds: 24 * 60 * 60 },
  { unit: 'hour', seconds: 60 * 60 },
  { unit: 'minute', seconds: 60 },
  { unit: 'second', seconds: 1 },
]

export function formatRelative(iso: string, now: Date = new Date()): string {
  const diffSeconds = (new Date(iso).getTime() - now.getTime()) / 1000

  // `RELATIVE_UNITS` sempre termina em `second`, que casa com a condição para qualquer
  // `diffSeconds` — `find` nunca devolve `undefined` na prática; o `!` só resolve o tipo.
  const { unit, seconds } = RELATIVE_UNITS.find(
    (candidate) => Math.abs(diffSeconds) >= candidate.seconds || candidate.unit === 'second',
  )!
  return relativeTimeFormatter.format(Math.round(diffSeconds / seconds), unit)
}

export function truncate(text: string, max: number): string {
  const normalized = text.replace(/\s+/g, ' ').trim()
  if (normalized.length <= max) return normalized

  const sliced = normalized.slice(0, max)
  const lastSpace = sliced.lastIndexOf(' ')
  const cut = lastSpace > 0 ? sliced.slice(0, lastSpace) : sliced
  return `${cut}…`
}

export function formatTemperature(temperature: number): string {
  return temperatureFormatter.format(temperature)
}

/** Fração de 0 a 1 como porcentagem pt-BR (`0.5` → `50%`). */
export function formatPercent(ratio: number): string {
  return percentFormatter.format(ratio)
}
