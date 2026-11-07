# A.1 — Definition of the general acceptance criteria

Analyze the question below and produce the guidelines that the **final answer** delivered to the
user must satisfy.

## Question

{{user_question}}

## Instructions

Identify, from the question itself:

1. **Language** — the language in which the final answer must be written. It is the language in
   which the question is written, unless the question explicitly asks for another one. The language
   of these instructions never defines the language of the final answer.
2. **Structure and format** — the requested form of the output, for example the selection of one
   option among those offered, or the written development of an explanation. When no format is
   explicit, record only what follows from the type of request, without inventing presentation
   obligations.
3. **Mandatory terms and constraints** — the terms, conditions and limits that the question imposes
   and that the final answer must respect.
4. **Key topics** — the topics that must appear in the final content for the answer to be
   considered complete.

The criteria describe **the final answer**, not the solving process. Do not write criteria about
how to reason, which steps to follow or how to split the work.

Record the actual constraints of the request. Generic guidance such as "be objective" or "answer
briefly" does not authorize arbitrary line or word limits. Numeric limits are included only when
they were explicitly requested. Distinguish an optional justification from a mandatory one: if the
user says "you may justify", do not require a justification; if they say "justify", preserve that
content obligation. The internal explanation of the tasks does not make an explanation mandatory in
the final answer.

**Do not solve the question at this stage.** No criterion may contain, suggest or anticipate the
answer to the question, nor list concepts, terms or statements from the options in order to approve
or discard them in advance.

In **multiple-choice questions**, state that the correct option must be the one that is
**relatively most coherent and best supported** by the question compared with the others (best fit
by elimination). Do not require a 100% literal word-for-word match, and do not forbid paraphrases,
syntheses or reasonable interpretive inferences in a way that would make every option invalid. When
the choice depends on a calculated value, do not require an exact numeric match nor forbid choosing
the option with the closest value: an approximation is acceptable as long as one of the options is
selected.

Each criterion receives its own identifier, in the form `AC1`, `AC2`, and so on.

## Examples of valid and invalid criteria

- Request: "Indicate the option objectively; you may justify". Valid: "Indicate the correct option
  objectively, with an optional justification". Invalid: "Use exactly two lines and justify
  mandatorily" — both obligations were invented.
- Request: "Answer in two lines and justify". Valid: preserve the two lines and the mandatory
  justification. Invalid: treat the requested justification as optional because the answer is short.
- Request: "Answer with the letter only". Valid: restrict the final presentation to the letter.
  Invalid: forbid explanations in the internal results or require every task to already contain the
  answer in the final format. This example does not determine which letter is correct.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"general_acceptance_criteria": [{"id": "AC1", "description": "..."}]}
