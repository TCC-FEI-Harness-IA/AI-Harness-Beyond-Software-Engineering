# Fontes oficiais e auditoria

Ampliação conferida em 7 de novembro de 2026. O corpus contém 270 questões reais e 24 PDFs oficiais arquivados: 12 cadernos de provas e seus 12 gabaritos.

- [CATALOG.md](CATALOG.md): procedência das 270 questões, incluindo disciplina, instituição, edição, fase, caderno, número original, páginas e links oficiais.
- [manifest.json](manifest.json): os mesmos vínculos em formato estruturado, com hashes SHA-256 dos PDFs, enunciados e respostas. `proof_pages` conta a capa como página 1 e inclui contextos compartilhados necessários.
- [official_answer_keys.json](official_answer_keys.json): gabaritos reextraídos dos PDFs oficiais. `null` indica anulação, nunca selecionada. Para o primeiro dia do ENEM, somente Humanas (46–90) é registrada, evitando a ambiguidade dos idiomas estrangeiros em Linguagens.
- [preserved_vestibular_90.json](preserved_vestibular_90.json): hashes dos 180 arquivos das 90 questões anteriores a esta ampliação.
- [preserved_originals.json](preserved_originals.json): registro anterior dos 30 arquivos das 15 questões originais do ENEM 2023.
- `*-proof.pdf` e `*-key.pdf`: cópias completas dos documentos oficiais, com URLs e hashes no manifesto.

| Fonte | Edição e prova | Gabarito utilizado |
| --- | --- | --- |
| enem20 | ENEM 2020 regular, 2º dia, caderno 7 azul; aplicado em 24/01/2021 | Oficial do acervo, com Q135 e Q157 anuladas |
| enem22d1 | ENEM 2022 regular, 1º dia, caderno 1 azul | Oficial do acervo; questões 46–90 |
| enem23d1 | ENEM 2023 regular, 1º dia, caderno 1 azul | Oficial do acervo; questões 46–90 |
| enem24d1 | ENEM 2024 regular, 1º dia, caderno 1 azul | Oficial do acervo; questões 46–90 |
| enem22 | ENEM 2022 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q157 anulada |
| enem23 | ENEM 2023 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q164 anulada |
| enem24 | ENEM 2024 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q129 anulada |
| enem25 | ENEM 2025 regular, 2º dia, caderno 7 azul | Oficial do acervo, com Q123, Q132 e Q174 anuladas |
| fuvest24 | FUVEST 2024, 1ª fase, prova V | Retificado em 24/11/2023; Q48 corrigida para E |
| ita24 | ITA 2024, 1ª fase, caderno único | Oficial do acervo, com Q10 anulada |
| ita25 | ITA 2025, 1ª fase, caderno único | Oficial do acervo, com Q9 e Q18 anuladas |
| unicamp25 | UNICAMP 2025, 1ª fase, provas Q e Z | `QZ_gabarito_2025_FINAL_site.pdf`, com Q53 anulada |

As cópias locais fixam as revisões utilizadas. Nenhuma dessas questões anuladas faz parte da bateria. Os identificadores, textos e respostas das 90 questões anteriores permanecem intactos.

Para repetir a auditoria a partir de `apps/backend`:

```sh
python -m pip install PyMuPDF==2.1
python scripts/verify_benchmark_sources.py
```

PyMuPDF é uma dependência opcional de auditoria, dispensável para carregar o corpus, executar o backend ou rodar os testes de integridade. O script não acessa a rede: verifica os hashes dos 24 PDFs, as páginas referenciadas e as 270 respostas diretamente nos gabaritos arquivados. Para a FUVEST, considera somente a prova V e a resposta final após a retificação.

A extração automática não substitui a revisão dos enunciados. A conferência das transcrições combina leitura dos textos extraídos com inspeção das páginas renderizadas para fórmulas, radicais, tabelas e quebras entre colunas. Os resultados e limites da validação estão em [VALIDATION.md](../VALIDATION.md).
