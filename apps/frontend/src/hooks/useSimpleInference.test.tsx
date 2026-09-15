import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { HttpError } from '../api/errors/HttpError'
import * as messageApi from '../api/messageApi'
import type * as MessageApiModule from '../api/messageApi'
import type { RunConfig } from '../api/messageApi'
import type { DefaultOutputDTO } from '../domain/types/defaultOutput'
import { useSimpleInference } from './useSimpleInference'

vi.mock('../api/messageApi', async () => {
  const actual = await vi.importActual<typeof MessageApiModule>('../api/messageApi')
  return { ...actual, sendDefaultMessage: vi.fn() }
})

const CONFIG: RunConfig = {
  modelName: 'openai/gpt-4o-mini',
  provider: 'open_router',
  maxTokens: 1000,
  temperature: 0.3,
}

const RESPONSE: DefaultOutputDTO = {
  message: 'Quais são todos os números primos entre 0 e 20?',
  response: 'Os números primos entre 0 e 20 são: 2, 3, 5, 7, 11, 13, 17, 19.',
  session_id: 'sess_ab12cd34ef56',
  tokens_input: 42,
  tokens_output: 118,
  inference_time_ms: 812,
}

const sendDefaultMessageMock = messageApi.sendDefaultMessage as Mock

afterEach(() => {
  sendDefaultMessageMock.mockReset()
})

describe('useSimpleInference', () => {
  it('a mensagem do usuário aparece antes da resposta chegar', async () => {
    let resolveResponse: (value: DefaultOutputDTO) => void = () => {}
    sendDefaultMessageMock.mockImplementation(
      () =>
        new Promise<DefaultOutputDTO>((resolve) => {
          resolveResponse = resolve
        }),
    )

    const { result } = renderHook(() => useSimpleInference(CONFIG))

    act(() => {
      result.current.send(RESPONSE.message)
    })

    expect(result.current.run.messages).toHaveLength(1)
    expect(result.current.run.messages[0]).toMatchObject({ role: 'user', content: RESPONSE.message })
    expect(result.current.isBusy).toBe(true)

    await act(async () => {
      resolveResponse(RESPONSE)
      await Promise.resolve()
    })
  })

  it('sucesso acrescenta a resposta com as estatísticas', async () => {
    sendDefaultMessageMock.mockResolvedValue(RESPONSE)
    const { result } = renderHook(() => useSimpleInference(CONFIG))

    act(() => {
      result.current.send(RESPONSE.message)
    })

    await waitFor(() => expect(result.current.run.messages).toHaveLength(2))
    expect(result.current.run.messages[1]).toMatchObject({
      role: 'assistant',
      content: RESPONSE.response,
    })
    expect(result.current.run.messages[1]?.stats?.totalTokens).toBe(160)
    expect(result.current.run.status).toBe('completed')
    expect(result.current.isBusy).toBe(false)
  })

  it('erro preserva a pergunta e retry refaz a chamada com o mesmo payload', async () => {
    sendDefaultMessageMock.mockRejectedValueOnce(new HttpError(500, 'falha no provedor'))
    sendDefaultMessageMock.mockResolvedValueOnce(RESPONSE)

    const { result } = renderHook(() => useSimpleInference(CONFIG))

    act(() => {
      result.current.send(RESPONSE.message)
    })

    await waitFor(() => expect(result.current.run.status).toBe('failed'))
    expect(result.current.run.messages).toHaveLength(1)
    expect(result.current.run.error).not.toBeNull()

    act(() => {
      result.current.retry()
    })

    await waitFor(() => expect(result.current.run.status).toBe('completed'))
    expect(sendDefaultMessageMock).toHaveBeenCalledTimes(2)

    const [firstPayload] = sendDefaultMessageMock.mock.calls[0] as [unknown]
    const [secondPayload] = sendDefaultMessageMock.mock.calls[1] as [unknown]
    expect(secondPayload).toEqual(firstPayload)
  })

  it('desmontar durante a chamada não gera aviso de setState após unmount', async () => {
    const warnSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    let resolveResponse: (value: DefaultOutputDTO) => void = () => {}
    sendDefaultMessageMock.mockImplementation(
      () =>
        new Promise<DefaultOutputDTO>((resolve) => {
          resolveResponse = resolve
        }),
    )

    const { result, unmount } = renderHook(() => useSimpleInference(CONFIG))
    act(() => {
      result.current.send(RESPONSE.message)
    })
    unmount()
    resolveResponse(RESPONSE)

    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(warnSpy).not.toHaveBeenCalled()
    warnSpy.mockRestore()
  })

  it('send durante isBusy é ignorado', () => {
    sendDefaultMessageMock.mockImplementation(() => new Promise<DefaultOutputDTO>(() => {}))
    const { result } = renderHook(() => useSimpleInference(CONFIG))

    act(() => {
      result.current.send('primeira pergunta')
    })
    act(() => {
      result.current.send('segunda pergunta')
    })

    expect(sendDefaultMessageMock).toHaveBeenCalledTimes(1)
    expect(result.current.run.messages).toHaveLength(1)
  })
})
