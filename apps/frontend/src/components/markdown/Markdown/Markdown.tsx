import { memo } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cx } from '@/components/cx'
import styles from './Markdown.module.css'

export interface MarkdownProps {
  content: string
  /** 'bubble' herda a cor do container (bolha azul do usuário); 'block' usa as cores padrão. */
  variant?: 'block' | 'bubble'
}

function TableWrapper(props: ComponentPropsWithoutRef<'table'>): JSX.Element {
  return (
    <div className={styles.tableWrapper}>
      <table {...props} />
    </div>
  )
}

function ExternalLink(props: ComponentPropsWithoutRef<'a'>): JSX.Element {
  return <a {...props} target="_blank" rel="noreferrer" />
}

/**
 * Único ponto do app que fala com `react-markdown` (README, regra de reuso 4). Nunca habilita
 * `rehype-raw` nem `dangerouslySetInnerHTML`: o conteúdo vem de um LLM e HTML cru é vetor de
 * XSS — sem `rehype-raw`, `react-markdown` já escapa tudo por padrão.
 */
export const Markdown = memo(function Markdown({ content, variant = 'block' }: MarkdownProps): JSX.Element {
  return (
    <div className={cx(styles.content, variant === 'bubble' && styles.bubble)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ table: TableWrapper, a: ExternalLink }}>
        {content}
      </ReactMarkdown>
    </div>
  )
})
