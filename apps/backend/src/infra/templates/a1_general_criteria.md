# A.1 — Definition of the general acceptance criteria

Analyze the question below and produce the guidelines that the **final answer** delivered to the
user must satisfy. Extract obligations from the request; do not solve it.

## Question

{{user_question}}

## Instructions

Identify, from the question itself:

1. **Language** — the language in which the final answer must be written. It is the language in
   which the question is written, unless the question explicitly asks for another one. The language
   of these instructions never defines the language of the final answer.
2. **Structure and format** — the requested form of the output, for example the selection of one
   option or a written explanation. When no format is explicit, record only what follows from the
   request, without inventing presentation obligations.
3. **Mandatory content to determine** — the quantities, relations, interpretations or other
   determinations actually requested, with units and references when specified. State what must be
   answered, without stating the answer. A request for a period requires that period, not just a
   distance ratio that could help calculate it.
4. **Explicit constraints** — the conditions and limits imposed by the request. Require literal
   terms only when the user explicitly requires that wording; otherwise allow equivalent meaning.

The criteria describe **the final answer**, not the solving process. Do not prescribe reasoning
steps or a decomposition. Keep mandatory content separate from optional presentation. Generic
guidance such as "be objective" does not authorize arbitrary line or word limits. Numeric limits
belong in the criteria only when explicitly requested. Distinguish an optional justification from
a mandatory one: "you may justify" does not require justification; "justify" does. Internal
explanations of tasks do not make an explanation mandatory in the final answer.

Do not turn a possible method, an unrequested proof, a preferred interpretation or an arbitrary
numerical tolerance into an obligation. A request for two consequences does not imply one positive
and one negative consequence. Do not require an answer marker unless requested.

**Do not solve the question at this stage.** No criterion may contain, suggest or anticipate the
answer, nor list concepts, terms or statements from the options in order to approve or discard them
in advance. A distractor's vocabulary is not mandatory content merely because it appears among
the offered options.

In **multiple-choice questions**, require the relatively most coherent and best-supported option
(best fit by elimination). Admit paraphrases, syntheses and reasonable contextual inferences rather
than requiring a 100% literal word-for-word match. When a choice depends on a calculated value,
allow a supported approximation: rounding or a closest value may justify a choice when consistent
with the data, applicable model and precision. Do not require exact coincidence or a direct
calculation reaching the option's value as a universal condition: elimination and contextual
inference may also support a choice. For an open question that admits an estimate, do not require
an exact value unless the request asks for one. Do not invent a numerical tolerance or treat the
mere selection of an option as evidence of correctness. An unexplained discrepancy is not justified
by selecting something.

Each criterion receives its own identifier, in the form `AC1`, `AC2`, and so on.

## Examples of valid and invalid criteria

- Request: "Indicate the option objectively; you may justify". Valid: "Indicate the supported
  option objectively, with an optional justification". Invalid: "Use exactly two lines and justify
  mandatorily" — both obligations were invented.
- Request: "Answer in two lines and justify". Valid: preserve the two lines and the mandatory
  justification. Invalid: treat the justification as optional because the answer is short.
- Request: "Answer with the letter only". Valid: restrict the final presentation to the letter.
  Invalid: forbid explanations in internal results or require every task to contain the answer in
  final format. This example does not determine which letter is correct.
- Request: "List two possible effects; you may justify". Valid: two relevant effects, with an
  optional final justification. Invalid: prescribe their positive or negative classification,
  demand a proof or import wording from an offered distractor.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"general_acceptance_criteria": [{"id": "AC1", "description": "..."}]}
