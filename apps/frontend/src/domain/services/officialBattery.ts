// Uma publicação oficial vira um documento de bateria cujo `id` é o da publicação (`pub_...`):
// assim telas, links e a análise distinguem resultado oficial de bateria pessoal pelo próprio id,
// sem misturar a cópia publicada com a bateria de origem.

import type { BenchmarkSessionDocument } from '../types/benchmarkSession'
import type { OfficialPublication } from '../types/officialPublication'

export function officialAsDocument(publication: OfficialPublication): BenchmarkSessionDocument {
  return { ...publication.battery, id: publication.id }
}
