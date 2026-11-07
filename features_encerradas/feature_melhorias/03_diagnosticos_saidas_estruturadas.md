## Contexto Geral

- O backend dessa aplicação deve reproduzir o fluxo proposto de adaptação do Ralph Loop do meu paper.
- O README.md contém uma explicação geral de todo o repositório.
- O RALPH_LOOP_ADAPTADO.md contém uma explicação detalhada de como deve funcionar a adaptação do Ralph Loop proposta no paper.

## Cenario Atual

O parser valida JSON, tipos, campos, identificadores de critérios e coerência dos vereditos. A sessão registra saídas recusadas, consumo e `finish_reason`. Entretanto, `PhaseParsingError` e `InvalidOutput` representam os problemas principalmente por mensagens textuais, dificultando distinguir sintaxe inválida, contrato inválido e truncamento.

No benchmark, Q056 de Química ITA terminou uma string por limite de comprimento; Q042 de Matemática ITA produziu JSON inválido com término `stop`; Q163 recebeu um campo com tipo errado; Q037 recebeu uma decisão incompatível com as avaliações. Essas ocorrências precisam ser identificadas separadamente. Uma chamada respondida com sucesso pelo provedor ainda pode produzir conteúdo recusado pelo parser.

## Sua tarefa

Modele diagnósticos estruturados associados à invocação de origem, preservando também o motivo legível e a saída bruta auditada. Registre:

- Estado da extração/sintaxe: válido, inválido ou válido após reparo.
- Estado do contrato: válido, inválido ou não avaliado.
- Código do problema, como `json_syntax`, `schema_type`, `missing_field`, `criteria_ids` e `decision_consistency`, com campo/critério afetado quando disponível.
- `finish_reason` original e indicador separado de interrupção por comprimento. Sem confirmação do provedor, registre apenas indício, não truncamento confirmado.
- Estratégia de recuperação, vínculo à invocação original e resultado da recuperação.

Trate truncamento como informação independente: uma saída pode estar truncada e ter sintaxe inválida; também pode terminar com `length` e formar JSON válido, sem garantia de completude semântica. Não conte duas vezes uma única saída apenas porque ela apresenta dois diagnósticos.

Mantenha a validação estrita. Não preencha avaliações ausentes, converta tipos por suposição nem force uma decisão para aceitar a resposta. Uma reprovação válida de B.2/C.1 é um resultado semântico normal, não erro de protocolo. Preserve o significado do desfecho do provedor e registre separadamente a aceitação ou recusa do conteúdo.

Implemente os contratos no domínio, a produção dos diagnósticos no parser e a persistência pelo recorder/mappers/repositórios existentes. Preserve os campos na consulta e exportação das sessões. Leia documentos antigos sem os novos campos, usando ausência/desconhecido em vez de presumir sucesso. Não altere a política de orçamento nem o fluxo analítico.

Cubra com testes as quatro classes de falha descritas, reparos locais, saída com `length` e JSON válido, associação à invocação, recuperação bem-sucedida e falha terminal. Verifique persistência JSON/MongoDB, exportação, compatibilidade com sessões antigas e contabilização das chamadas, conforme os adapters existentes.

## Metodo de desenvolvimento:

- O desenvolvimento deve ser feito obrigatoriamente em uma **Git worktree exclusiva**, com uma **branch própria para esta correção**, pois outros agentes estão desenvolvendo simultaneamente no mesmo repositório. Crie a worktree antes de alterar código, testes ou documentação e execute nela todas as alterações e verificações.
- Preserve as alterações dos outros agentes: não reutilize suas worktrees ou branches, não reverta nem sobrescreva trabalho alheio e não faça operações destrutivas no repositório compartilhado. Na integração, resolva eventuais conflitos preservando as mudanças compatíveis, especialmente nos arquivos de documentação comuns.
- A aplicação deve ser desenvolvida usando TDD, ou seja, devem ser construídos TESTES que garantam o comportamento corrigido da aplicação, e depois disso deve ser feito o código que respeita esse comportamento.

## Documentação das alterações:

- Por se tratar de uma alteração na regra de funcionamento do Ralph Loop adaptado, atualize o arquivo `RALPH_LOOP_ADAPTADO.md`, que possui uma explicação detalhada do funcionamento do Ralph Loop adaptado.
- Também documente com detalhes como funciona a nova lógica, fornecendo exemplos e atualizando o arquivo existente `NOVAS_REGRAS_RALPH_LOOP.md`. Se ele não existir, crie-o com esse nome. Esse relatório será usado posteriormente para atualizar o paper oficial, contendo os novos ajustes.
- Documente os diagnósticos como tratamento operacional, sem apresentá-los como uma nova etapa de raciocínio do paper. Preserve a transcrição literal da metodologia original.
