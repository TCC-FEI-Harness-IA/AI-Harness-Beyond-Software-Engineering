import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PhaseTag } from './PhaseTag'

describe('PhaseTag', () => {
  it('em A.3 o learn é identificado como aprendizados do enunciado', () => {
    render(<PhaseTag phase="A3" subtype="learn" />)

    expect(screen.getByText('A.3 · Aprendizados do enunciado')).toBeInTheDocument()
  })

  it('em B.4 o learn continua sendo os aprendizados extraídos da tarefa', () => {
    render(<PhaseTag phase="B4" subtype="learn" taskId="T1" />)

    expect(screen.getByText('B.4 · Aprendizados extraídos')).toBeInTheDocument()
    expect(screen.getByText('T1')).toBeInTheDocument()
  })

  it('sem tarefa (etapa global como A.3) não renderiza a etiqueta de tarefa', () => {
    render(<PhaseTag phase="A3" subtype="learn" taskId={null} />)

    expect(screen.queryByText('setup')).not.toBeInTheDocument()
  })
})
