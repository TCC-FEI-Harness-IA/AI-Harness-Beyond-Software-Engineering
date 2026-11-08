// Duplo controlável de WebSocket para testes (README, FASE 02, seção 12). Nenhum teste abre
// uma conexão real — os testes instanciam esta classe no lugar de `globalThis.WebSocket` e
// disparam os eventos manualmente.

type GenericListener = (event: Event) => void
type MessageListener = (event: MessageEvent) => void
type CloseListener = (event: CloseEvent) => void

// Tipo de armazenamento interno — `Event` é a base comum de `MessageEvent`/`CloseEvent`,
// então qualquer listener guardado aqui pode ser chamado com o evento concreto.
type StoredListener = (event: Event) => void

// `never` é assinável a partir de qualquer tipo de parâmetro (é o tipo bottom), então serve
// como assinatura de implementação compatível com todos os overloads de `addEventListener`
// abaixo — a mesma correlação não verificável estaticamente que faz o `addEventListener`
// nativo do DOM não ser tipado por dentro do seu próprio corpo.
type ImplListener = (event: never) => void

export class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  public readonly url: string
  public sentFrames: string[] = []
  public closeCalls: Array<number | undefined> = []

  private listeners: Record<'open' | 'message' | 'close' | 'error', StoredListener[]> = {
    open: [],
    message: [],
    close: [],
    error: [],
  }

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  addEventListener(type: 'open', listener: GenericListener): void
  addEventListener(type: 'message', listener: MessageListener): void
  addEventListener(type: 'close', listener: CloseListener): void
  addEventListener(type: 'error', listener: GenericListener): void
  addEventListener(type: 'open' | 'message' | 'close' | 'error', listener: ImplListener): void {
    this.listeners[type].push(listener as unknown as StoredListener)
  }

  removeEventListener(type: 'open', listener: GenericListener): void
  removeEventListener(type: 'message', listener: MessageListener): void
  removeEventListener(type: 'close', listener: CloseListener): void
  removeEventListener(type: 'error', listener: GenericListener): void
  removeEventListener(type: 'open' | 'message' | 'close' | 'error', listener: ImplListener): void {
    const list = this.listeners[type]
    const index = list.indexOf(listener as unknown as StoredListener)
    if (index >= 0) list.splice(index, 1)
  }

  send(data: string): void {
    this.sentFrames.push(data)
  }

  close(code?: number): void {
    this.closeCalls.push(code)
  }

  // --- controles de teste ---

  emitOpen(): void {
    const event = {} as Event
    this.listeners.open.forEach((listener) => listener(event))
  }

  emitMessage(data: unknown): void {
    const event = { data: typeof data === 'string' ? data : JSON.stringify(data) } as MessageEvent
    this.listeners.message.forEach((listener) => listener(event))
  }

  emitClose(code: number): void {
    const event = { code } as CloseEvent
    this.listeners.close.forEach((listener) => listener(event))
  }

  emitError(): void {
    const event = {} as Event
    this.listeners.error.forEach((listener) => listener(event))
  }

  static reset(): void {
    FakeWebSocket.instances = []
  }

  static latest(): FakeWebSocket {
    const instance = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
    if (!instance) throw new Error('Nenhuma instância de FakeWebSocket foi criada.')
    return instance
  }
}
