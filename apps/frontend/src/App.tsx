import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

// ── Types ──────────────────────────────────────────────────────────────────

type Phase = 'idle' | 'streaming' | 'done'

type Subtype =
  | 'setup' | 'tasks'
  | 'execute' | 'reasoning' | 'verify_pass' | 'verify_fail'
  | 'store' | 'learn' | 'reset'
  | 'compile' | 'result'

type Task = 'setup' | 'T1' | 'T2' | 'T3' | 'synthesis'

interface ContextWindow { context_id: string; context_size: number }

interface Chunk {
  type: 'thinking' | 'result'
  subtype?: Subtype
  task?: Task
  content: string
  total_tokens?: number
  context_window?: ContextWindow
}

interface ThinkingEntry {
  subtype: Subtype
  task: Task
  content: string
  totalTokens?: number
  contextId?: string
  contextSize?: number
}

// ── Color per task (drives all visual accents) ─────────────────────────────

const TASK_COLOR: Record<Task, string> = {
  setup:     '#6366f1', // indigo  — fase A
  T1:        '#a78bfa', // violeta — Tarefa 1
  T2:        '#3b82f6', // azul    — Tarefa 2
  T3:        '#10b981', // esmeralda — Tarefa 3
  synthesis: '#f59e0b', // âmbar   — fase C
}

// ── Label per subtype (independent of color) ──────────────────────────────

const SUBTYPE_LABEL: Record<Subtype, string> = {
  setup:       'Configuração',
  tasks:       'Tarefas',
  execute:     'Execução',
  reasoning:   'Raciocínio',
  verify_pass: 'Verificação ✓',
  verify_fail: 'Verificação ✗',
  store:       'Armazenamento',
  learn:       'Aprendizado',
  reset:       'Reset',
  compile:     'Compilação',
  result:      'Resultado',
}

// ── Helpers ────────────────────────────────────────────────────────────────

function Md({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className="md"
      components={{ a: (p) => <a {...p} target="_blank" rel="noreferrer" /> }}
    >
      {children}
    </ReactMarkdown>
  )
}

function phaseLabelFor(i: number, entries: ThinkingEntry[]): string | null {
  if (i === 0) return 'A — Setup'
  const prev = entries[i - 1].subtype
  const curr = entries[i].subtype
  const inB = (s: Subtype) =>
    ['execute', 'reasoning', 'verify_pass', 'verify_fail', 'store', 'learn', 'reset'].includes(s)
  const inC = (s: Subtype) => s === 'compile'
  if (!inB(prev) && inB(curr)) return 'B — Loop de Raciocínio'
  if (!inC(prev) && inC(curr)) return 'C — Síntese Final'
  return null
}

// ── App ────────────────────────────────────────────────────────────────────

export default function App() {
  const [phase, setPhase]             = useState<Phase>('idle')
  const [heroMounted, setHeroMounted] = useState(true)
  const [heroExiting, setHeroExiting] = useState(false)
  const [chatActive, setChatActive]   = useState(false)   // panels + footer visible
  const [entries, setEntries]         = useState<ThinkingEntry[]>([])
  // track the active task so we inherit its color for subsequent subtypes
  const activeTaskRef = useRef<Task>('setup')
  const [result, setResult]           = useState('')
  const [input, setInput]             = useState('')
  const [expanded, setExpanded]         = useState(false)
  const [selectedFlow, setSelectedFlow] = useState<'simple' | 'ralph_wiggum'>('ralph_wiggum')
  const [selectedModel, setSelectedModel] = useState<'8B' | '70B' | '405B'>('8B')

  const thinkingRef    = useRef<HTMLDivElement>(null)
  const footerInputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll thinking panel
  useEffect(() => {
    if (thinkingRef.current) {
      thinkingRef.current.scrollTop = thinkingRef.current.scrollHeight
    }
  }, [entries])

  // Focus footer input once hero is gone
  useEffect(() => {
    if (!heroMounted && chatActive && !expanded) {
      footerInputRef.current?.focus()
    }
  }, [heroMounted, chatActive, expanded])

  // ── Streaming ────────────────────────────────────────────────────────────

  const doStream = async (trimmed: string) => {
    try {
      const res = await fetch('/v1/message/reasoning', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: { user_input: trimmed },
          llm_model_config: {
            provider: 'open_router',
            provider_config: { model_name: 'openai/gpt-4o-mini' },
            max_tokens: 512,
          },
          reasoning_config: {
            phase_breaking_strategy: 'predefined',
            strategies: { predefined: { number_of_phases: 3 } },
            next_phase_strategy: 'algorithmic',
          },
        }),
      })

      const reader  = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const chunk: Chunk = JSON.parse(raw)
            if (chunk.type === 'thinking') {
              const task: Task = chunk.task ?? activeTaskRef.current
              activeTaskRef.current = task
              setEntries((p) => [...p, {
                subtype: chunk.subtype ?? 'execute',
                task,
                content: chunk.content,
                totalTokens: chunk.total_tokens,
                contextId: chunk.context_window?.context_id,
                contextSize: chunk.context_window?.context_size,
              }])
            } else if (chunk.type === 'result') {
              setResult(chunk.content)
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setEntries((p) => [...p, { subtype: 'execute', content: `**Erro:** ${msg}` }])
    } finally {
      setPhase('done')
    }
  }

  // ── Send ─────────────────────────────────────────────────────────────────

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || phase === 'streaming') return

    setInput('')
    setEntries([])
    setResult('')
    setPhase('streaming')
    activeTaskRef.current = 'setup'

    if (!chatActive) {
      // First send: animate hero out, reveal chat layout
      setHeroExiting(true)
      setChatActive(true)
      setTimeout(() => setHeroMounted(false), 440)
    }

    doStream(trimmed)
  }

  const onInputKey  = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { e.preventDefault(); handleSend() }
  }
  const onAreaKey   = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleSend() }
  }

  const isDone = phase === 'done'

  // ── Input field (shared state, rendered in two places) ───────────────────

  const heroInput = expanded ? (
    <textarea
      className="chat-field chat-field--area"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={onAreaKey}
      placeholder="Faça uma pergunta... (Ctrl+Enter para enviar)"
      disabled={phase === 'streaming'}
      autoFocus
    />
  ) : (
    <input
      className="chat-field"
      type="text"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={onInputKey}
      placeholder="Faça uma pergunta..."
      disabled={phase === 'streaming'}
      autoFocus
    />
  )

  const footerInput = expanded ? (
    <textarea
      className="chat-field chat-field--area"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={onAreaKey}
      placeholder="Faça uma pergunta... (Ctrl+Enter para enviar)"
      disabled={phase === 'streaming'}
      tabIndex={chatActive ? 0 : -1}
    />
  ) : (
    <input
      ref={footerInputRef}
      className="chat-field"
      type="text"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={onInputKey}
      placeholder="Faça uma pergunta..."
      disabled={phase === 'streaming'}
      tabIndex={chatActive ? 0 : -1}
    />
  )

  const expandBtn = (
    <button
      className="expand-btn"
      onClick={() => setExpanded((v) => !v)}
      title={expanded ? 'Recolher' : 'Expandir'}
    >
      {expanded ? '↙' : '↗'}
    </button>
  )

  const sendBtn = (
    <button
      className="send-btn"
      onClick={handleSend}
      disabled={phase === 'streaming' || !input.trim()}
    >
      {phase === 'streaming' ? '...' : 'Enviar'}
    </button>
  )

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="app">
      {/* Header — always visible */}
      <header className="app-header">
        <span className="app-header__title">Ralph Wiggum Loop</span>
        <span className="app-header__subtitle">
          Harness de IA · Resolução de Perguntas em Linguagem Natural
        </span>
        {phase === 'streaming' && (
          <span className="app-header__badge">processando...</span>
        )}
      </header>

      {/* Body — panels + footer behind hero overlay */}
      <div className="app-body">

        {/* ── Panels ── */}
        <main className={`panels${isDone ? ' panels--split' : ''}`}>
          <div className="panel thinking-panel">
            <div className="panel__label">
              Open Thinking
              {entries.length > 0 && (
                <span className="panel__count">{entries.length} etapas</span>
              )}
            </div>
            <div className="panel__content" ref={thinkingRef}>
              <div className="timeline">
                {entries.map((entry, i) => {
                  const color    = TASK_COLOR[entry.task] ?? TASK_COLOR.setup
                  const label    = phaseLabelFor(i, entries)
                  const isLast   = i === entries.length - 1
                  const isActive = isLast && phase === 'streaming'
                  // connecting line: gradient toward next entry's task color (or border if last)
                  const nextColor = entries[i + 1] ? TASK_COLOR[entries[i + 1].task] ?? color : undefined
                  return (
                    <div key={i}>
                      {label && (
                        <div className="timeline__phase-sep"><span>{label}</span></div>
                      )}
                      <div className="timeline__item">
                        <div className="timeline__rail">
                          <div
                            className={`timeline__dot${isActive ? ' timeline__dot--pulse' : ''}`}
                            style={{ background: color, boxShadow: `0 0 0 3px ${color}28` }}
                          />
                          {!isLast && (
                            <div
                              className="timeline__line"
                              style={{
                                background: nextColor && nextColor !== color
                                  ? `linear-gradient(to bottom, ${color}80, ${nextColor}80)`
                                  : `linear-gradient(to bottom, ${color}60, var(--border))`,
                              }}
                            />
                          )}
                        </div>
                        <div
                          className={`msg-card${isActive ? ' msg-card--active' : ''}`}
                          style={{ borderColor: isActive ? color : undefined }}
                        >
                          <div
                            className="msg-card__tag"
                            style={{ color, borderColor: `${color}40`, background: `${color}12` }}
                          >
                            {SUBTYPE_LABEL[entry.subtype] ?? entry.subtype}
                          </div>
                          <Md>{entry.content}</Md>
                          {entry.contextId && (() => {
                            const prevCtxId = i > 0 ? entries[i - 1].contextId : undefined
                            const ctxChanges = entry.contextId !== prevCtxId
                            const seenBefore = i > 0 && entries.slice(0, i).some(e => e.contextId === entry.contextId)
                            const isNewCtx    = ctxChanges && !seenBefore
                            const isReturnCtx = ctxChanges && seenBefore
                            return (
                              <div className={`msg-card__meta${isNewCtx ? ' msg-card__meta--new-ctx' : isReturnCtx ? ' msg-card__meta--return-ctx' : ''}`}>
                                <span className="msg-card__meta-left">
                                  <span className={`msg-card__ctx-id${isNewCtx ? ' msg-card__ctx-id--new' : isReturnCtx ? ' msg-card__ctx-id--return' : ''}`}>
                                    {entry.contextId}
                                  </span>
                                  {isNewCtx && (
                                    <span className="msg-card__ctx-badge">↺ nova janela</span>
                                  )}
                                  {isReturnCtx && (
                                    <span className="msg-card__ctx-badge msg-card__ctx-badge--return">↩ janela retomada</span>
                                  )}
                                  <span className="msg-card__ctx-size">
                                    {entry.contextSize?.toLocaleString('pt-BR')} tk
                                  </span>
                                </span>
                                <span className="msg-card__meta-right">
                                  Σ {entry.totalTokens?.toLocaleString('pt-BR')} tk
                                </span>
                              </div>
                            )
                          })()}
                        </div>
                      </div>
                    </div>
                  )
                })}

                {phase === 'streaming' && entries.length > 0 && (
                  <div className="timeline__item timeline__item--cursor">
                    <div className="timeline__rail">
                      <span className="cursor-dot" />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className={`panel result-panel${isDone ? ' result-panel--visible' : ''}`}>
            <div className="panel__label">Result</div>
            <div className="panel__content panel__content--center">
              {isDone && result && (
                <div className="result-card">
                  <p className="result-card__text">{result}</p>
                  <p className="result-card__caption">resposta gerada pelo harness</p>
                </div>
              )}
            </div>
          </div>
        </main>

        {/* ── Footer chat bar (behind hero, animates in on first send) ── */}
        <footer className={`chat-bar${chatActive ? ' chat-bar--active' : ' chat-bar--dormant'}`}>
          <div className={`input-wrap${expanded ? ' input-wrap--expanded' : ''}`}>
            {footerInput}
            {expandBtn}
          </div>
          {sendBtn}
        </footer>

        {/* ── Hero overlay (covers body, exits on first send) ── */}
        {heroMounted && (
          <div className={`hero-overlay${heroExiting ? ' hero-overlay--exit' : ''}`}>
            <div className="hero__inner">
              <div className="hero__brand">
                <h2 className="hero__name">Ralph Wiggum Loop</h2>
                <p className="hero__tagline">
                  Harness de IA para Resolução de Perguntas em Linguagem Natural
                </p>
              </div>

              <div className="hero__selectors">
                <div className="selector-group">
                  <span className="selector-group__label">Fluxo</span>
                  <div className="selector-group__btns">
                    {([
                      { id: 'simple',       label: 'Inferência simples' },
                      { id: 'ralph_wiggum', label: 'Ralph Wiggum Loop' },
                    ] as const).map(({ id, label }) => (
                      <button
                        key={id}
                        className={`selector-btn${selectedFlow === id ? ' selector-btn--active' : ''}`}
                        onClick={() => setSelectedFlow(id)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="selector-group">
                  <span className="selector-group__label">Modelo</span>
                  <div className="selector-group__btns">
                    {(['8B', '70B', '405B'] as const).map((size) => (
                      <button
                        key={size}
                        className={`selector-btn${selectedModel === size ? ' selector-btn--active' : ''}`}
                        onClick={() => setSelectedModel(size)}
                      >
                        Llama 3.1 {size}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className={`hero__bar${expanded ? ' hero__bar--expanded' : ''}`}>
                <div className={`input-wrap${expanded ? ' input-wrap--expanded' : ''}`}>
                  {heroInput}
                  {expandBtn}
                </div>
                {sendBtn}
              </div>

              {expanded && (
                <p className="hero__hint">Ctrl+Enter para enviar</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
