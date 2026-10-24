import { describe, expect, it } from 'vitest'
import { getStepLabel, SUBTYPE_LABEL } from './eventSubtype'
import { isThinkingPhase, PHASE_LABEL, PHASE_SHORT_LABEL, THINKING_PHASE } from './thinkingPhase'

describe('THINKING_PHASE', () => {
  it('inclui A.3 — aprendizados pontuais do enunciado — entre A.2 e B.1', () => {
    const phases = Object.values(THINKING_PHASE)

    expect(THINKING_PHASE.A3).toBe('A3')
    expect(phases.indexOf('A3')).toBe(phases.indexOf('A2') + 1)
    expect(phases.indexOf('B1')).toBe(phases.indexOf('A3') + 1)
  })

  it('reconhece A3 na fronteira, como as demais fases', () => {
    expect(isThinkingPhase('A3')).toBe(true)
    expect(isThinkingPhase('A4')).toBe(false)
  })

  it('toda fase tem rótulo completo e curto', () => {
    for (const phase of Object.values(THINKING_PHASE)) {
      expect(PHASE_LABEL[phase]).toBeTruthy()
      expect(PHASE_SHORT_LABEL[phase]).toBeTruthy()
    }
    expect(PHASE_LABEL.A3).toBe('Aprendizados do enunciado')
    expect(PHASE_SHORT_LABEL.A3).toBe('A.3')
  })
})

describe('getStepLabel', () => {
  it('em A.3 o evento learn fala do enunciado, não de uma tarefa', () => {
    expect(getStepLabel(THINKING_PHASE.A3, 'learn')).toBe('Aprendizados do enunciado')
  })

  it('em B.4 o evento learn continua sendo os aprendizados extraídos da tarefa', () => {
    expect(getStepLabel(THINKING_PHASE.B4, 'learn')).toBe(SUBTYPE_LABEL.learn)
  })

  it('nas demais combinações usa o rótulo do subtype', () => {
    expect(getStepLabel(THINKING_PHASE.A2, 'tasks')).toBe(SUBTYPE_LABEL.tasks)
  })
})
