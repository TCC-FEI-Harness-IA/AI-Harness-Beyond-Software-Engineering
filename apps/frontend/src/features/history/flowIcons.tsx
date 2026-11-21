// Ícones de fluxo compartilhados entre `SessionCard` e `HistorySidebar` (regra de reuso 2 do
// README — usados em mais de um lugar, viram um módulo só). Mesmo vocabulário visual dos
// cartões da home (raio = simples, órbita = Ralph), redesenhado em traço mais fino para caber
// ao lado de texto pequeno.

export const SIMPLE_FLOW_ICON = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
  </svg>
)

export const RALPH_FLOW_ICON = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <circle cx="12" cy="12" r="2.4" />
    <ellipse cx="12" cy="12" rx="9.5" ry="4" transform="rotate(30 12 12)" />
  </svg>
)
