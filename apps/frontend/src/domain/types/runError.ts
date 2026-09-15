// Forma estrutural mínima de um erro exibível dentro do domínio (README, seção 6.3, campo
// `error` do view-model). `domain/` não pode importar de `api/` (README, seção 6.1), então este
// tipo não importa `AppError` de `src/api/errors` — qualquer `AppError` real satisfaz esta forma
// por tipagem estrutural, o mesmo padrão já usado por `DisplayableError` em `ErrorState`.
export interface RunError {
  message: string
  userMessage: string
}
