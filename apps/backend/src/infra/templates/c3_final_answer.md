# C.3 — Construction of the final answer

Organize and present the results already produced as the final answer to the user.

## Stored results

{{stored_results}}

## General acceptance criteria

{{general_acceptance_criteria}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them only to
check the question data when presenting the answer — for example, the letter of the option that
corresponds to the value obtained in the results.
The learnings **do not replace the stored results**: the content of the answer still comes
exclusively from them.

{{learnings}}

## Instructions

Write the answer in the **language** and in the **structure** defined by the general criteria,
respecting the terms and constraints they impose. If the stored results are written in another
language, translate the content faithfully into the required language: translating is presentation,
not new reasoning.

This stage is about **presentation, not reasoning**. It is strictly forbidden to:

- introduce new facts that are not in the stored results;
- speculate, assume or infer what the results do not support;
- perform new analytical reasoning about the problem.

Use exclusively the material from the stored results. In multiple-choice questions, carefully check
the table of options in **Key Learnings** to ensure that the chosen letter corresponds to the option
selected in the stored results — including when they chose it as the one whose value is closest to
the calculated one, which is a valid selection. The final answer goes in the `final_answer` field,
in markdown.

Apply the final language, format and constraints without new analytical reasoning. The internal
results may contain explanations even when the final request only admits the letter. Omit or
present the justification according to the general criteria: optional does not mean mandatory, and
an explicitly required justification must come from the already approved grounding. Do not invent
line or word limits from a generic guideline of objectivity.

## Examples of valid and invalid presentation

- The results already identify C and explain the calculation; request "only the letter". Valid:
  `C`. Invalid: copying the internal explanation into the answer despite that restriction.
- Same results; request "end with FINAL_ANSWER: LETTER". Valid: apply the line `FINAL_ANSWER: C`,
  even though it does not appear literally in the internal results. The same holds for any marker
  line the request defines, which must be reproduced exactly as requested.
- Request "justify": present the approved grounding. Request "you may justify": it is optional,
  respecting the other constraints. Invalid: inventing a proof or a calculation to fill a missing
  justification.
- Invalid: performing the intersection of conditions only checked in isolation or selecting an
  option not yet supported. That would be new analytical content, not formatting.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"final_answer": "markdown of the answer to the user"}
