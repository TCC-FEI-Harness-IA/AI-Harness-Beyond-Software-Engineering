// Único lugar do app com texto de erro voltado ao usuário (README, FASE 02, seção 6). Toda
// mensagem exibida em tela sai daqui — nenhuma string de erro escrita dentro de componente.

const HTTP_STATUS_MESSAGE: Record<number, string> = {
  400: 'O registro deste chat está corrompido.',
  401: 'Sua sessão terminou. Faça login novamente.',
  403: 'A operação foi recusada por segurança. Recarregue a página e tente de novo.',
  404: 'Chat não encontrado.',
  409: 'A operação não é possível no estado atual do recurso.',
  422: 'Os parâmetros enviados não são aceitos pelo servidor.',
  428: 'Configure a sua chave OpenRouter para executar chamadas ao modelo.',
  429: 'Muitas execuções ou tentativas em pouco tempo. Aguarde e tente de novo.',
  500: 'O servidor falhou ao processar a requisição.',
  503: 'Um serviço necessário está indisponível no momento.',
}

const HTTP_STATUS_FALLBACK = 'O servidor respondeu com um erro inesperado.'

export function httpStatusMessage(status: number): string {
  return HTTP_STATUS_MESSAGE[status] ?? HTTP_STATUS_FALLBACK
}

const WS_CLOSE_CODE_MESSAGE: Record<number, string> = {
  1003: 'O servidor recusou os parâmetros enviados.',
  1008: 'A conexão foi recusada: origem não permitida.',
  1009: 'A pergunta é grande demais para o servidor.',
  1011: 'A execução falhou no servidor.',
  4401: 'Sua sessão terminou e a execução foi interrompida. Faça login novamente.',
  4428: 'Configure ou corrija a sua chave OpenRouter para executar.',
  4429: 'Você atingiu o limite de execuções simultâneas ou por período. Aguarde e tente de novo.',
  4503: 'O serviço de autenticação está indisponível. Tente novamente em instantes.',
}

/** Código de fechamento que significa "sessão de autenticação encerrada". */
export const WS_CLOSE_UNAUTHENTICATED = 4401

const WS_CLOSE_CODE_FALLBACK = 'A conexão com o servidor foi encerrada de forma inesperada.'

export function wsCloseCodeMessage(code: number): string {
  return WS_CLOSE_CODE_MESSAGE[code] ?? WS_CLOSE_CODE_FALLBACK
}

export const NETWORK_ERROR_MESSAGE = 'Não foi possível falar com o servidor.'
export const TIMEOUT_ERROR_MESSAGE = 'O servidor demorou demais para responder.'
export const CONTRACT_ERROR_MESSAGE = 'O servidor respondeu em um formato inesperado.'
export const CANCELED_ERROR_MESSAGE = 'A execução foi cancelada.'
export const WS_OPEN_TIMEOUT_MESSAGE = 'Não foi possível abrir a conexão com o servidor a tempo.'
