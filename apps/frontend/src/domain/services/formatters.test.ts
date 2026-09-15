import { describe, expect, it } from 'vitest'
import {
  formatCompactTokens,
  formatDateTime,
  formatDuration,
  formatRelative,
  formatTemperature,
  formatTokens,
  truncate,
} from './formatters'

describe('formatTokens', () => {
  it('agrupa milhares no padrão pt-BR', () => {
    expect(formatTokens(15284)).toBe('15.284')
  })
})

describe('formatCompactTokens', () => {
  it('compacta em "mil" com uma casa decimal', () => {
    // Intl usa um espaço fino (NBSP) entre o número e a unidade — não é um espaço comum.
    expect(formatCompactTokens(15284)).toBe('15,3 mil')
  })
})

describe('formatDuration', () => {
  it('mostra milissegundos abaixo de 1s', () => {
    expect(formatDuration(812)).toBe('812 ms')
  })

  it('mostra segundos com uma casa decimal abaixo de 1min', () => {
    expect(formatDuration(5230)).toBe('5,2 s')
  })

  it('mostra minutos e segundos acima de 1min', () => {
    expect(formatDuration(64000)).toBe('1 min 4 s')
  })

  it('omite segundos quando o resto é exatamente zero', () => {
    expect(formatDuration(120000)).toBe('2 min')
  })
})

describe('formatDateTime', () => {
  it('formata data e hora no padrão pt-BR', () => {
    expect(formatDateTime('2026-09-11T23:18:06.314083+00:00')).toMatch(
      /^\d{2}\/\d{2}\/\d{4}, \d{2}:\d{2}$/,
    )
  })
})

describe('formatRelative', () => {
  it('formata minutos passados como "há N minutos"', () => {
    const now = new Date('2026-09-11T23:21:06.000Z')
    const iso = '2026-09-11T23:18:06.000Z'
    expect(formatRelative(iso, now)).toBe('há 3 minutos')
  })
})

describe('truncate', () => {
  it('não corta texto dentro do limite', () => {
    expect(truncate('texto curto', 100)).toBe('texto curto')
  })

  it('corta na fronteira de palavra, nunca no meio de uma palavra', () => {
    const text = 'Quais são todos os números primos entre 0 e 20?'
    expect(truncate(text, 20)).toBe('Quais são todos os…')
  })

  it('normaliza quebras de linha para espaço', () => {
    expect(truncate('linha um\nlinha dois', 100)).toBe('linha um linha dois')
  })
})

describe('formatTemperature', () => {
  it('formata com vírgula decimal', () => {
    expect(formatTemperature(0.3)).toBe('0,3')
  })
})
