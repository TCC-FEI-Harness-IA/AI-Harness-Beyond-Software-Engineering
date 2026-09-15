// Traçados SVG (14px, traço 1.5) de cada subtipo de evento (README, FASE 03, seção 6). Um
// mapa de dados — não um componente — para não multiplicar 11 arquivos de componente por
// um só ícone cada (regra 1 do README é sobre componentes, não sobre dados de apoio).

import type { EventSubtype } from '@/domain/enums/eventSubtype'

export const SUBTYPE_ICON_PATH: Record<EventSubtype, string> = {
  setup: 'M4 5h9M4 9h9M4 13h6M3 3v10',
  tasks: 'M3 3h4v4H3V3Zm6 0h4v4H9V3ZM3 9h4v4H3V9Zm6 0h4v4H9V9Z',
  execute: 'M4 2.5v11l9-5.5-9-5.5Z',
  reasoning: 'M7 2a5 5 0 0 0-3 9v1.5h6V11a5 5 0 0 0-3-9ZM5.5 14.5h3',
  verify_pass: 'M3 8l3 3 6-7',
  verify_fail: 'M12 4a5.5 5.5 0 1 0 1.5 5M13 2v3.5H9.5',
  store: 'M2 5h11v8H2V5Zm0 0 1.5-3h8L13 5',
  learn: 'M7 1.5a3.5 3.5 0 0 1 2 6.4V10h-4V7.9A3.5 3.5 0 0 1 7 1.5ZM5.5 12h3',
  reset: 'M8 1 3 8h3.5L6 14l6-8H8.5L8 1Z',
  compile: 'M7 2 1.5 5 7 8l5.5-3L7 2ZM1.5 8 7 11l5.5-3M1.5 11 7 14l5.5-3',
  replan: 'M4 2v6a3 3 0 0 0 3 3h3M4 2 1.5 4.5M4 2l2.5 2.5M10 8v3',
}
