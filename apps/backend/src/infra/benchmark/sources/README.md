# Fontes oficiais e auditoria

Consulta e conferência: 25 de outubro de 2026.

- [CATALOG.md](CATALOG.md): procedência das 90 questões, com disciplina, instituição, edição, fase, caderno, número original, páginas necessárias e links oficiais da prova e do gabarito.
- [manifest.json](manifest.json): o mesmo vínculo em formato estruturado, mais hashes SHA-256 dos documentos oficiais, enunciados e respostas. `proof_pages` usa a posição no PDF contando a capa; inclui páginas de constantes e contextos compartilhados. A identificação da prova e sua versão ficam em `sources[source_id]`.
- [official_answer_keys.json](official_answer_keys.json): transcrição dos sete gabaritos oficiais, extraível novamente dos PDFs. `null` indica anulação, nunca selecionada no corpus. Para a FUVEST, somente a coluna da prova V é registrada; a questão 48, não selecionada, contém a correção definitiva para E.
- [preserved_originals.json](preserved_originals.json): hashes dos 30 arquivos das 15 questões existentes, calculados no snapshot de integração `605efd0` e conferidos antes da entrega.
- `*-proof.pdf` e `*-key.pdf`: cópias completas dos documentos baixados diretamente das instituições, sem reexportação ou alterações. Os URLs e hashes estão no manifesto.

| Fonte | Instituição responsável | Edição e prova | Gabarito utilizado |
| --- | --- | --- | --- |
| enem22 | Inep | ENEM 2022 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q157 anulada |
| enem23 | Inep | ENEM 2023 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q164 anulada |
| enem24 | Inep | ENEM 2024 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q129 anulada |
| fuvest24 | FUVEST / Universidade de São Paulo | Vestibular 2024, 1ª fase, prova V | Retificado em 24/11/2023 |
| ita24 | Instituto Tecnológico de Aeronáutica | Vestibular 2024, 1ª fase, caderno único | Oficial do acervo, com Q10 anulada |
| ita25 | Instituto Tecnológico de Aeronáutica | Vestibular 2025, 1ª fase, caderno único | Oficial do acervo, com Q9 e Q18 anuladas |
| unicamp25 | Comvest / Universidade Estadual de Campinas | Vestibular 2025, 1ª fase, provas Q e Z | `QZ_gabarito_2025_FINAL_site.pdf`, com Q53 anulada |

O corpus não contém nenhuma dessas questões anuladas. As cópias locais fixam as revisões verificadas, permitindo auditar o conteúdo mesmo se os sites forem alterados. A nomenclatura original e eventuais peculiaridades de redação das provas foram preservadas.

Para repetir a auditoria dos gabaritos em PDF, a partir de `apps/backend`, execute:

```sh
python -m pip install PyMuPDF==2.0
python scripts/verify_benchmark_sources.py
```

PyMuPDF é uma dependência opcional de auditoria e não é necessário para carregar questões, executar o backend ou rodar sua suíte de testes. O script não acessa a rede e verifica os hashes dos 14 PDFs, as páginas do manifesto e as 90 respostas diretamente nos sete PDFs de gabaritos. Na FUVEST, a extração considera somente a prova V e a letra final após a retificação.

A transcrição dos enunciados exige também leitura visual dos originais: a extração de texto de PDF pode perder índices, acentos, frações e quebras entre colunas. Essa revisão foi realizada para os itens selecionados; a checagem automática de respostas não substitui essa etapa.
