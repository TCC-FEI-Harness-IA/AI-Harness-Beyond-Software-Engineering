import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LoopArc } from './LoopArc'

describe('LoopArc', () => {
  it.each([
    ['plan-revision', true, /revisão do plano A\.3 → A\.2: pelo menos um plano candidato foi reprovado/],
    ['plan-revision', false, /revisão do plano A\.3 → A\.2, ainda não acionado/],
    ['verify-retry', true, /retentativa B\.1 ⇄ B\.2: pelo menos uma verificação/],
    ['replan-return', false, /C\.2 para B, ainda não acionado/],
  ] as const)('o arco %s (ativo: %s) descreve o retorno', (id, active, label) => {
    render(<LoopArc arc={{ id, active }} />)

    expect(screen.getByRole('img', { name: label })).toBeInTheDocument()
  })
})
