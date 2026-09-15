// Status HTTP >= 400. Carrega o `status` e o `detail` que o FastAPI devolve no corpo
// (`{ "detail": "..." }`), quando presente.

import { AppError } from './AppError'
import { httpStatusMessage } from './messages'

export class HttpError extends AppError {
  public readonly status: number
  public readonly detail: string | null

  constructor(status: number, detail: string | null) {
    super(`HTTP ${status}: ${detail ?? '(sem detail)'}`, httpStatusMessage(status))
    this.status = status
    this.detail = detail
  }
}
