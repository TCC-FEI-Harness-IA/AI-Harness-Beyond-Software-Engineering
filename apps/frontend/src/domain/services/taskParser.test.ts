import { describe, expect, it } from 'vitest'
import fixture from '@/test/fixtures/session-a1-completed-15msgs.json'
import {
  extractTaskBlock,
  parseCriterionEvaluations,
  parseDecision,
  parseTaskTitle,
  parseTasksFromMarkdown,
} from './taskParser'

const TASKS_MARKDOWN = fixture.messages.find((message) => message.order === 2)?.content ?? ''
const VERIFICATION_MARKDOWN = fixture.messages.find((message) => message.order === 5)?.content ?? ''

describe('parseTasksFromMarkdown', () => {
  it('extrai as 2 tarefas reais de A2, com título e critérios', () => {
    const tasks = parseTasksFromMarkdown(TASKS_MARKDOWN)

    expect(tasks).toHaveLength(2)
    expect(tasks[0]).toMatchObject({
      id: 'T1',
      title: 'Identificar números primos no intervalo de 0 a 10',
    })
    expect(tasks[1]).toMatchObject({
      id: 'T2',
      title: 'Identificar números primos no intervalo de 11 a 20',
    })

    expect(tasks[0]?.criteria).toEqual([
      { id: 'T1-AC1', text: 'A saída contém exclusivamente números primos do intervalo [0, 10].' },
      {
        id: 'T1-AC2',
        text: 'A saída não inclui números compostos ou não primos como 0, 1, 4, 6, 8, 9, 10.',
      },
      {
        id: 'T1-AC3',
        text: 'A tarefa não tenta resolver o problema para números maiores que 10; a saída não contém nenhum número fora do intervalo 0-10.',
      },
    ])

    expect(tasks[0]?.expectedInput).toContain('Nenhum input externo')
    expect(tasks[0]?.expectedOutput).toContain('Lista de números primos')
  })

  it('markdown fora do formato devolve array vazio, sem lançar', () => {
    expect(parseTasksFromMarkdown('texto qualquer sem cabeçalho')).toEqual([])
    expect(() => parseTasksFromMarkdown('')).not.toThrow()
  })

  it('tarefa sem corpo (cabeçalho seguido de outro cabeçalho) tem description null', () => {
    const tasks = parseTasksFromMarkdown('### T1 — Primeira\n### T2 — Segunda\ncorpo da T2')
    expect(tasks[0]?.description).toBeNull()
  })

  it('corpo que começa direto com um campo em negrito (sem parágrafo descritivo) tem description null', () => {
    const tasks = parseTasksFromMarkdown('### T1 — Título\n**Entrada esperada:** um número')
    expect(tasks[0]?.description).toBeNull()
    expect(tasks[0]?.expectedInput).toBe('um número')
  })
})

describe('parseTasksFromMarkdown — critérios em inglês', () => {
  it('lê os critérios escritos pelo backend atual (`**Acceptance criteria:**`), além do formato antigo', () => {
    const markdown = [
      '## Planned tasks',
      '',
      '### T1 — Testar as condições',
      '',
      'Descrição.',
      '',
      '**Depends on:** `T0`',
      '',
      '**Acceptance criteria:**',
      '- `T1-AC1`: Determinar quais números atendem.',
      '- `T1-AC2`: Explicar cada teste.',
    ].join('\n')

    expect(parseTasksFromMarkdown(markdown)[0]?.criteria).toEqual([
      { id: 'T1-AC1', text: 'Determinar quais números atendem.' },
      { id: 'T1-AC2', text: 'Explicar cada teste.' },
    ])
  })
})

describe('extractTaskBlock', () => {
  it('devolve o bloco da tarefa exatamente como foi escrito, até a tarefa seguinte', () => {
    const t1 = '### T1 — A\n\nDescrição.\n\n**Acceptance criteria:**\n- `T1-AC1`: x.'
    const t2 = '### T2 — B\n\nOutra.\n\n**Depends on:** `T1`\n\n**Acceptance criteria:**\n- `T2-AC1`: y.'
    const markdown = `## Planned tasks\n\n${t1}\n\n${t2}`

    expect(extractTaskBlock(markdown, 'T1')).toBe(t1)
    expect(extractTaskBlock(markdown, 'T2')).toBe(t2)
    expect(extractTaskBlock(markdown, 'T3')).toBeNull()
  })
})

describe('parseTaskTitle', () => {
  it('extrai o título da primeira tarefa', () => {
    expect(parseTaskTitle(TASKS_MARKDOWN)).toBe('Identificar números primos no intervalo de 0 a 10')
  })

  it('devolve null quando não há cabeçalho de tarefa', () => {
    expect(parseTaskTitle('sem cabeçalho nenhum')).toBeNull()
  })
})

describe('parseTaskTitle e parseTasksFromMarkdown na mesma execução', () => {
  it('ler o título de uma tarefa não faz a leitura seguinte das tarefas devolver vazio', () => {
    // Regressão: `parseTaskTitle` usava `exec` numa regex global e deixava `lastIndex` sujo, o que
    // fazia o `matchAll` seguinte começar no meio do texto — e perder as tarefas de um replan.
    expect(parseTaskTitle(TASKS_MARKDOWN)).not.toBeNull()

    expect(parseTasksFromMarkdown(TASKS_MARKDOWN).length).toBeGreaterThan(0)
    expect(parseTasksFromMarkdown(TASKS_MARKDOWN)[0]?.id).toBe('T1')
  })
})

describe('parseDecision', () => {
  it('reconhece approved e reproved', () => {
    expect(parseDecision(VERIFICATION_MARKDOWN)).toBe('approved')
    expect(parseDecision('**Decisão:** `reproved`\n\n- algo')).toBe('reproved')
  })

  it('devolve null quando o marcador não existe', () => {
    expect(parseDecision('texto sem decisão')).toBeNull()
  })
})

describe('parseCriterionEvaluations', () => {
  it('lê as avaliações de critério da verificação real', () => {
    const evaluations = parseCriterionEvaluations(VERIFICATION_MARKDOWN)

    expect(evaluations).toHaveLength(3)
    expect(evaluations[0]).toMatchObject({ id: 'T1-AC1', met: true })
    expect(evaluations[0]?.justification).toContain('A saída [2, 3, 5, 7]')
  })

  it('reconhece avaliações não atendidas', () => {
    const evaluations = parseCriterionEvaluations('- `T1-AC1` — não atendido: faltou algo')
    expect(evaluations).toEqual([{ id: 'T1-AC1', met: false, justification: 'faltou algo' }])
  })

  it('markdown fora do formato devolve array vazio, sem lançar', () => {
    expect(parseCriterionEvaluations('texto qualquer')).toEqual([])
  })
})
