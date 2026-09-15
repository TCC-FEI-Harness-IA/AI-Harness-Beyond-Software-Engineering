// Testes de integração de tela (README, FASE 08, seção 6.2): cobrem os três fluxos que o TCC
// demonstra, de ponta a ponta pelo `AppRouter` real, com duplos de rede — nenhum teste fala
// com o backend de verdade.

import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import a1Completed from '@/test/fixtures/session-a1-completed-15msgs.json'
import directCompleted from '@/test/fixtures/session-direct-completed.json'
import { FakeWebSocket } from '@/test/doubles/FakeWebSocket'
import { AppRouter } from '@/router/AppRouter'
import { RunConfigProvider } from '@/state/RunConfigContext'
import { ThemeProvider } from '@/state/ThemeContext'
import { ViewModeProvider } from '@/state/ViewModeContext'
import { EVENT_SUBTYPE, type EventSubtype } from '@/domain/enums/eventSubtype'
import { EVENT_TYPE, type EventType } from '@/domain/enums/eventType'
import { TASK_LABEL_SETUP, TASK_LABEL_SYNTHESIS } from '@/domain/enums/taskLabels'
import type { ThinkingPhase } from '@/domain/enums/thinkingPhase'

function renderApp(initialPath: string): void {
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <RunConfigProvider>
          <ViewModeProvider>
            <AppRouter />
          </ViewModeProvider>
        </RunConfigProvider>
      </ThemeProvider>
    </MemoryRouter>,
  )
}

function jsonResponse(status: number, body: unknown): Response {
  return { status, text: () => Promise.resolve(JSON.stringify(body)) } as Response
}

// Mesma metadados de evento usados em `reasoningRunReducer.test.ts` (FASE 05, seção 11) —
// deriva a sequência de eventos ao vivo do fixture real com 2 tarefas de 5 passos cada.
const EVENT_META: Array<{ order: number; subtype: EventSubtype; type: EventType; task: string }> = [
  { order: 1, subtype: EVENT_SUBTYPE.SETUP, type: EVENT_TYPE.THINKING, task: TASK_LABEL_SETUP },
  { order: 2, subtype: EVENT_SUBTYPE.TASKS, type: EVENT_TYPE.THINKING, task: TASK_LABEL_SETUP },
  { order: 3, subtype: EVENT_SUBTYPE.RESET, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 4, subtype: EVENT_SUBTYPE.REASONING, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 5, subtype: EVENT_SUBTYPE.VERIFY_PASS, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 6, subtype: EVENT_SUBTYPE.STORE, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 7, subtype: EVENT_SUBTYPE.LEARN, type: EVENT_TYPE.THINKING, task: 'T1' },
  { order: 8, subtype: EVENT_SUBTYPE.RESET, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 9, subtype: EVENT_SUBTYPE.REASONING, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 10, subtype: EVENT_SUBTYPE.VERIFY_PASS, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 11, subtype: EVENT_SUBTYPE.STORE, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 12, subtype: EVENT_SUBTYPE.LEARN, type: EVENT_TYPE.THINKING, task: 'T2' },
  { order: 13, subtype: EVENT_SUBTYPE.COMPILE, type: EVENT_TYPE.THINKING, task: TASK_LABEL_SYNTHESIS },
  { order: 14, subtype: EVENT_SUBTYPE.COMPILE, type: EVENT_TYPE.RESULT, task: TASK_LABEL_SYNTHESIS },
]

function buildFixtureEvents(): unknown[] {
  let cumulative = 0
  return EVENT_META.map(({ order, subtype, type, task }) => {
    const message = a1Completed.messages.find((candidate) => candidate.order === order)
    if (!message) throw new Error(`fixture sem mensagem de order ${order}`)
    cumulative += message.total_tokens
    return {
      type,
      subtype,
      phase: message.phase as ThinkingPhase,
      task,
      session_id: a1Completed.id,
      content: message.content,
      total_tokens: cumulative,
      context_window: { context_id: message.context_id ?? '', context_size: message.total_tokens },
      inference_time_ms: message.inference_time_ms,
    }
  })
}

describe('Fluxo simples completo (home → inferência simples → estatísticas)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('home → escrever → escolher Inferência Simples → resposta com estatísticas na tela', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        message: 'Quais são todos os números primos entre 0 e 20?',
        response: 'Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19.',
        session_id: 'sess_simple_test',
        tokens_input: 42,
        tokens_output: 118,
        inference_time_ms: 812,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    renderApp('/')

    await user.type(screen.getByRole('textbox'), 'Quais são todos os números primos entre 0 e 20?')
    await user.click(screen.getByRole('radio', { name: /Inferência Simples/ }))

    expect(await screen.findByText(/Os números primos entre 0 e 20 são/)).toBeInTheDocument()
    // Estatísticas por mensagem (tokens/tempo/modelo) aparecem junto com a resposta.
    expect(screen.getAllByText(/812 ms|0,8 s/).length).toBeGreaterThan(0)
  })
})

describe('Fluxo Ralph completo (home → Ralph → Modo Chat → Modo Gráfico)', () => {
  beforeEach(() => {
    FakeWebSocket.reset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('emite a sequência real de eventos e mostra todos os passos, a resposta final e a trilha do Modo Gráfico', async () => {
    vi.stubGlobal('WebSocket', FakeWebSocket)
    const user = userEvent.setup()
    renderApp('/')

    await user.type(screen.getByRole('textbox'), a1Completed.user_question)
    await user.click(screen.getByRole('radio', { name: /Ralph Loop Adaptado/ }))

    const socket = await waitFor(() => FakeWebSocket.latest())
    act(() => {
      socket.emitOpen()
      for (const event of buildFixtureEvents()) {
        socket.emitMessage(event)
      }
      socket.emitClose(1000)
    })

    // Modo Chat (default): resposta final destacada.
    expect(await screen.findByText(new RegExp(a1Completed.final_answer!.slice(0, 20)))).toBeInTheDocument()

    // Alterna para o Modo Gráfico e confirma que as tarefas aparecem na trilha.
    await user.click(screen.getByRole('radio', { name: 'Gráfico' }))
    expect(await screen.findByText('T1')).toBeInTheDocument()
    expect(screen.getByText('T2')).toBeInTheDocument()
  })
})

describe('Histórico (lista → detalhe → dois modos → voltar sem nova requisição)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lista duas sessões, abre a Ralph, mostra a barra lateral, os dois modos funcionam, e voltar não refaz requisições', async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url.endsWith('/sessions')) {
        return Promise.resolve(jsonResponse(200, { session_ids: [a1Completed.id, directCompleted.id] }))
      }
      if (url.includes(a1Completed.id)) {
        return Promise.resolve(jsonResponse(200, a1Completed))
      }
      if (url.includes(directCompleted.id)) {
        return Promise.resolve(jsonResponse(200, directCompleted))
      }
      throw new Error(`URL inesperada no duplo de fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    renderApp('/historico')

    // As duas sessões aparecem na lista central.
    const historyList = await screen.findByRole('list')
    await waitFor(() => {
      expect(within(historyList).getAllByRole('link')).toHaveLength(2)
    })
    const callsAfterList = fetchMock.mock.calls.length

    // Abre a sessão Ralph (A1).
    await user.click(screen.getByRole('link', { name: new RegExp(a1Completed.user_question.slice(0, 15)) }))

    // Barra lateral reduzida presente, com as duas conversas.
    const sidebar = await screen.findByRole('navigation', { name: 'Conversas' })
    expect(within(sidebar).getAllByRole('link')).toHaveLength(2)

    // Modo Chat mostra a resposta final; alterna para o Modo Gráfico e volta.
    expect(await screen.findByText(new RegExp(a1Completed.final_answer!.slice(0, 20)))).toBeInTheDocument()
    await user.click(screen.getByRole('radio', { name: 'Gráfico' }))
    expect(await screen.findByText('T1')).toBeInTheDocument()
    await user.click(screen.getByRole('radio', { name: 'Chat' }))
    expect(await screen.findByText(new RegExp(a1Completed.final_answer!.slice(0, 20)))).toBeInTheDocument()

    // Volta para a lista pelo link "Histórico" da barra superior. `GET /v1/sessions` é
    // refeito por design (é leve, e a lista pode ter mudado — README/FASE 07, seção 4), mas
    // nenhum dos dois documentos é buscado de novo: os dois já estão no cache em memória.
    const docCallsBeforeBack = fetchMock.mock.calls.filter(
      ([url]: [string]) => url.includes(a1Completed.id) || url.includes(directCompleted.id),
    ).length
    await user.click(screen.getByRole('link', { name: 'Histórico' }))

    await waitFor(() => {
      expect(screen.getAllByRole('link', { name: new RegExp(a1Completed.user_question.slice(0, 15)) })).toHaveLength(1)
    })
    const docCallsAfterBack = fetchMock.mock.calls.filter(
      ([url]: [string]) => url.includes(a1Completed.id) || url.includes(directCompleted.id),
    ).length
    expect(docCallsAfterBack).toBe(docCallsBeforeBack)
    expect(callsAfterList).toBeGreaterThan(0)
  })
})
