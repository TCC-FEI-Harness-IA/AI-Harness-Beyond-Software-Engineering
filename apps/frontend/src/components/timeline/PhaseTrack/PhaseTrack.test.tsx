// Trilha macro com a versão do fluxo (nova fase de validação — 01): na versão 2 a trilha tem A.3
// (validação da decomposição), A.4 (aprendizados do enunciado) e o ciclo A.2 ⇄ A.3; numa sessão antiga
// A.3 continua sendo a extração do enunciado, sem esse ciclo.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import legacyFixture from '@/test/fixtures/session-a1-completed-with-a3.json'
import revisionCapture from '@/test/fixtures/capture-v2-plan-revision-c3-audit.json'
import { parseSessionDocument } from '@/api/parsers/sessionDocument'
import { sessionToThinkingRun } from '@/domain/services/sessionToThinkingRun'
import { PhaseTrack } from './PhaseTrack'

describe('PhaseTrack', () => {
  it('na versão 2 mostra A.3 de validação, A.4 de aprendizados e o ciclo de revisão do plano acionado', async () => {
    const run = sessionToThinkingRun(parseSessionDocument(revisionCapture.session))
    const onStepSelect = vi.fn()

    render(<PhaseTrack run={run} isLive={false} onStepSelect={onStepSelect} />)

    expect(screen.getByText('Validação da decomposição')).toBeInTheDocument()
    expect(screen.getByText('Aprendizados do enunciado')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: /Ciclo de revisão do plano A\.3 → A\.2: pelo menos um plano candidato/ }),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByText('A.4'))
    expect(onStepSelect).toHaveBeenLastCalledWith(expect.objectContaining({ phase: 'A4', subtype: 'learn' }))
    await userEvent.click(screen.getByText('A.3'))
    expect(onStepSelect).toHaveBeenLastCalledWith(expect.objectContaining({ phase: 'A3', subtype: 'tasks' }))
  })

  it('numa sessão antiga A.3 continua sendo aprendizados do enunciado, sem o ciclo do plano', () => {
    const run = sessionToThinkingRun(parseSessionDocument(legacyFixture))

    render(<PhaseTrack run={run} isLive={false} onStepSelect={vi.fn()} />)

    expect(screen.getByText('Aprendizados do enunciado')).toBeInTheDocument()
    expect(screen.queryByText('Validação da decomposição')).not.toBeInTheDocument()
    expect(screen.queryByText('A.4')).not.toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /revisão do plano/ })).not.toBeInTheDocument()
  })
})
