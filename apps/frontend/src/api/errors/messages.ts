// Único lugar do app com texto de erro voltado ao usuário (README, FASE 02, seção 6). Toda
// mensagem exibida em tela sai daqui — nenhuma string de erro escrita dentro de componente.

const HTTP_STATUS_MESSAGE: Record<number, string> = {
  400: 'O registro deste chat está corrompido.',
  404: 'Chat não encontrado.',
  422: 'Os parâmetros enviados não são aceitos pelo servidor.',
  500: 'O servidor falhou ao processar a requisição.',
}

const HTTP_STATUS_FALLBACK = 'O servidor respondeu com um erro inesperado.'

export function httpStatusMessage(status: number): string {
  return HTTP_STATUS_MESSAGE[status] ?? HTTP_STATUS_FALLBACK
}

const WS_CLOSE_CODE_MESSAGE: Record<number, string> = {
  1003: 'O servidor recusou os parâmetros enviados.',
  1009: 'A pergunta é grande demais para o servidor.',
  1011: 'A execução falhou no servidor.',
}

const WS_CLOSE_CODE_FALLBACK = 'A conexão com o servidor foi encerrada de forma inesperada.'

export function wsCloseCodeMessage(code: number): string {
  return WS_CLOSE_CODE_MESSAGE[code] ?? WS_CLOSE_CODE_FALLBACK
}

export const NETWORK_ERROR_MESSAGE = 'Não foi possível falar com o servidor.'
export const TIMEOUT_ERROR_MESSAGE = 'O servidor demorou demais para responder.'
export const CONTRACT_ERROR_MESSAGE = 'O servidor respondeu em um formato inesperado.'
export const WS_OPEN_TIMEOUT_MESSAGE = 'Não foi possível abrir a conexão com o servidor a tempo.'
