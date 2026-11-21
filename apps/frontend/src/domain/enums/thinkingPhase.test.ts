import { describe, expect, it } from 'vitest'
import { getStepLabel, SUBTYPE_LABEL, SUBTYPE_TONE } from './eventSubtype'
import { FLOW_VERSION } from './flowVersion'
import { getPhaseLabel, isThinkingPhase, PHASE_LABEL, PHASE_SHORT_LABEL, THINKING_PHASE } from './thinkingPhase'

describe('THINKING_PHASE', () => {
  it('inclui A.3 e A.4 entre A.2 e B.1', () => {
    const phases = Object.values(THINKING_PHASE)

    expect(THINKING_PHASE.A3).toBe('A3')
    expect(THINKING_PHASE.A4).toBe('A4')
    expect(phases.indexOf('A3')).toBe(phases.indexOf('A2') + 1)
    expect(phases.indexOf('A4')).toBe(phases.indexOf('A3') + 1)
    expect(phases.indexOf('B1')).toBe(phases.indexOf('A4') + 1)
  })

  it('reconhece A3 e A4 na fronteira, como as demais fases', () => {
    expect(isThinkingPhase('A3')).toBe(true)
    expect(isThinkingPhase('A4')).toBe(true)
    expect(isThinkingPhase('A5')).toBe(false)
  })

  it('toda fase tem rótulo completo e curto', () => {
    for (const phase of Object.values(THINKING_PHASE)) {
      expect(PHASE_LABEL[phase]).toBeTruthy()
      expect(PHASE_SHORT_LABEL[phase]).toBeTruthy()
    }
    expect(PHASE_SHORT_LABEL.A3).toBe('A.3')
    expect(PHASE_SHORT_LABEL.A4).toBe('A.4')
  })
})

describe('getPhaseLabel — o significado de A.3 depende da versão do fluxo', () => {
  it('no fluxo atual (versão 2), A.3 valida a decomposição e A.4 extrai os aprendizados do enunciado', () => {
    expect(getPhaseLabel(THINKING_PHASE.A3, FLOW_VERSION.VALIDATED_PLANNING)).toBe('Validação da decomposição')
    expect(getPhaseLabel(THINKING_PHASE.A4, FLOW_VERSION.VALIDATED_PLANNING)).toBe('Aprendizados do enunciado')
    expect(PHASE_LABEL.A3).toBe('Validação da decomposição')
  })

  it('numa sessão antiga (versão 1), A.3 continua sendo a extração dos aprendizados do enunciado', () => {
    expect(getPhaseLabel(THINKING_PHASE.A3, FLOW_VERSION.LEGACY)).toBe('Aprendizados do enunciado')
    expect(getPhaseLabel(THINKING_PHASE.B1, FLOW_VERSION.LEGACY)).toBe(PHASE_LABEL.B1)
  })
})

describe('getStepLabel', () => {
  it('em A.3 (sessão antiga) e em A.4 o evento learn fala do enunciado, não de uma tarefa', () => {
    expect(getStepLabel(THINKING_PHASE.A3, 'learn')).toBe('Aprendizados do enunciado')
    expect(getStepLabel(THINKING_PHASE.A4, 'learn')).toBe('Aprendizados do enunciado')
  })

  it('o plano candidato, a reprovação, a aprovação e a confirmação na fila têm rótulos distintos', () => {
    expect(getStepLabel(THINKING_PHASE.A2, 'plan_candidate')).toBe('Plano candidato')
    expect(getStepLabel(THINKING_PHASE.A3, 'plan_rejected')).toBe('Plano reprovado')
    expect(getStepLabel(THINKING_PHASE.A3, 'plan_approved')).toBe('Plano aprovado')
    expect(getStepLabel(THINKING_PHASE.A3, 'tasks')).toBe('Plano confirmado na fila')
    expect(SUBTYPE_TONE.plan_rejected).toBe('warning')
    expect(SUBTYPE_TONE.plan_approved).toBe('success')
  })

  it('em B.4 o evento learn continua sendo os aprendizados extraídos da tarefa', () => {
    expect(getStepLabel(THINKING_PHASE.B4, 'learn')).toBe(SUBTYPE_LABEL.learn)
  })

  it('nas demais combinações usa o rótulo do subtype', () => {
    expect(getStepLabel(THINKING_PHASE.A2, 'tasks')).toBe(SUBTYPE_LABEL.tasks)
  })
})
