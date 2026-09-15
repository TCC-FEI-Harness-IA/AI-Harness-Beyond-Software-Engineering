// View-model do fluxo baseline (README, FASE 04, seção 6). Passa pela camada de domínio mesmo
// sendo uma única chamada, para que a FASE 07 renderize uma sessão `DIRECT` persistida com
// exatamente esta mesma tela — só muda quem produz o `SimpleRun`.

import type { RunStatus } from '../enums/runStatus'
import type { MessageStatsView } from './messageStatsView'
import type { RunError } from './runError'
import type { RunTotals } from './runTotals'

export interface SimpleMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  stats: MessageStatsView | null
}

export interface SimpleRun {
  sessionId: string | null
  status: RunStatus
  messages: SimpleMessage[]
  totals: RunTotals | null
  error: RunError | null
}
