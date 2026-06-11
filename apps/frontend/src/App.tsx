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

interface Chunk { type: 'thinking' | 'result'; subtype?: Subtype; content: string }
interface ThinkingEntry { subtype: Subtype; content: string }

// ── Subtype config ─────────────────────────────────────────────────────────

const SUBTYPE: Record<Subtype, { color: string; label: string }> = {
  setup:       { color: '#6366f1', label: 'Configuração'  },
  tasks:       { color: '#3b82f6', label: 'Tarefas'       },
  execute:     { color: '#8b5cf6', label: 'Execução'      },
  reasoning:   { color: '#a78bfa', label: 'Raciocínio'    },
  verify_pass: { color: '#10b981', label: 'Verificação ✓' },
  verify_fail: { color: '#ef4444', label: 'Verificação ✗' },
  store:       { color: '#06b6d4', label: 'Armazenamento' },
  learn:       { color: '#f59e0b', label: 'Aprendizado'   },
  reset:       { color: '#f97316', label: 'Reset'         },
  compile:     { color: '#0ea5e9', label: 'Compilação'    },
  result:      { color: '#22c55e', label: 'Resultado'     },
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
  const [result, setResult]           = useState('')
  const [input, setInput]             = useState('')
  const [expanded, setExpanded]       = useState(false)

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
              setEntries((p) => [...p, { subtype: chunk.subtype ?? 'execute', content: chunk.content }])
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
                  const cfg      = SUBTYPE[entry.subtype] ?? SUBTYPE.execute
                  const label    = phaseLabelFor(i, entries)
                  const isLast   = i === entries.length - 1
                  const isActive = isLast && phase === 'streaming'
                  return (
                    <div key={i}>
                      {label && (
                        <div className="timeline__phase-sep"><span>{label}</span></div>
                      )}
                      <div className="timeline__item">
                        <div className="timeline__rail">
                          <div
                            className={`timeline__dot${isActive ? ' timeline__dot--pulse' : ''}`}
                            style={{ background: cfg.color, boxShadow: `0 0 0 3px ${cfg.color}28` }}
                          />
                          {!isLast && (
                            <div
                              className="timeline__line"
                              style={{ background: `linear-gradient(to bottom, ${cfg.color}60, var(--border))` }}
                            />
                          )}
                        </div>
                        <div
                          className={`msg-card${isActive ? ' msg-card--active' : ''}`}
                          style={{ borderColor: isActive ? cfg.color : undefined }}
                        >
                          <div
                            className="msg-card__tag"
                            style={{ color: cfg.color, borderColor: `${cfg.color}40`, background: `${cfg.color}12` }}
                          >
                            {cfg.label}
                          </div>
                          <Md>{entry.content}</Md>
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
