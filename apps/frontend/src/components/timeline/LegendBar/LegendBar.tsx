import styles from './LegendBar.module.css'

interface LegendItem {
  symbol: string
  label: string
  tone: 'context' | 'strong' | 'success' | 'warning' | 'secondary'
}

// A invariante mais importante do paper (README, seção 2 e FASE 06, seção 5): resultado
// alimenta a resposta final, aprendizado alimenta a próxima tarefa — e nunca o contrário. A
// legenda existe para que essa distinção não dependa de o leitor adivinhar pelo símbolo.
const ITEMS: LegendItem[] = [
  { symbol: '●', label: 'Reinício de contexto (Fresh Context)', tone: 'context' },
  { symbol: '◆', label: 'Resolução da tarefa (B.1)', tone: 'strong' },
  { symbol: '✓', label: 'Verificação aprovada', tone: 'success' },
  { symbol: '✗', label: 'Verificação reprovada — nova tentativa no mesmo contexto', tone: 'warning' },
  { symbol: '▣', label: 'Resultado armazenado → alimenta a resposta final', tone: 'success' },
  { symbol: '☀', label: 'Aprendizado extraído → alimenta a próxima tarefa', tone: 'secondary' },
]

/** Legenda fixa dos símbolos da faixa por tarefa (README, FASE 06, seção 5). */
export function LegendBar(): JSX.Element {
  return (
    <ul className={styles.legend}>
      {ITEMS.map((item) => (
        <li key={item.label} className={styles.item}>
          <span className={styles.symbol} data-tone={item.tone} aria-hidden="true">
            {item.symbol}
          </span>
          <span>{item.label}</span>
        </li>
      ))}
    </ul>
  )
}
