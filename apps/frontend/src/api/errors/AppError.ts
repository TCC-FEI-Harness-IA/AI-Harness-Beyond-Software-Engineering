// Classe base da hierarquia de erros tipados (README, FASE 02, seção 6). Toda falha de rede
// ou de contrato que a UI precisa mostrar carrega uma `userMessage` em português — nenhum
// componente monta a própria string de erro.

export abstract class AppError extends Error {
  public readonly userMessage: string

  protected constructor(message: string, userMessage: string) {
    super(message)
    this.name = new.target.name
    this.userMessage = userMessage
  }
}
