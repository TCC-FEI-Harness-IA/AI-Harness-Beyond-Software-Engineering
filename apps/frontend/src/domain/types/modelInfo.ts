/**
 * Um modelo do catálogo (`/v1/models`, coleção `models` do MongoDB), cadastrado na tela "Modelos".
 * Todo campo além do identificador é opcional — um dado ainda desconhecido fica `null`.
 */
export interface ModelInfo {
  model_name: string
  display_name: string | null
  /** Preço em USD por 1 milhão de tokens de entrada. */
  input_price_per_million_tokens: number | null
  /** Preço em USD por 1 milhão de tokens de saída. */
  output_price_per_million_tokens: number | null
  /** Contexto máximo, em tokens. */
  context_length: number | null
  /** Vazão típica, em tokens por segundo. */
  throughput_tokens_per_second: number | null
}
