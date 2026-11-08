# C.3 — Construction of the final answer

Organize and present the results already produced as the final answer to the user. The stored
results below are the current results exactly as the last global verification (C.1) approved them:
superseded conclusions and rejected attempts are not part of them, and they are the only source of
the content of the answer.

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
selected in the stored results — including when they chose it by best fit, approximation or
elimination with the grounding that C.1 approved. Present an approximate result as approximate and
an estimate as an estimate, keeping its stated hypotheses when the answer includes a justification;
never turn a best fit into an exact equality. Do not repair, recalculate or reconcile results here.
The final answer goes in the `final_answer` field, in markdown.

Apply the final language, format and constraints without new analytical reasoning. The internal
results may contain explanations even when the final request only admits the letter. Omit or
present the justification according to the general criteria: optional does not mean mandatory, and
an explicitly required justification must come from the already approved grounding. Do not invent
line or word limits from a generic guideline of objectivity.

## Fidelity check before answering

Do this check within this same response, before writing `final_answer`. It is part of the
presentation, not a separate stage, and it does not reopen what C.1 approved.

1. **Approved content.** First identify the approved content that answers each part of the request:
   the object, value, choice or conclusion determined by the stored results, and the result that
   supports it.
2. **Preserved aspects.** The text you write must keep, unchanged: the meaning; the direction of
   every comparison (greater or smaller, increases or decreases, and which object each one refers
   to); signs; units and the reference frame; references to objects, periods and sources; hypotheses
   and conditions; and qualifiers such as "approximately", "under hypothesis X", "best fit" or
   "estimate". Translation and concision change the wording, never these aspects.
3. **Calculated result and approved choice.** Distinguish a calculated result from a choice
   approved by best fit, approximation or elimination, and present each with the nature the results
   gave it. When the obtained value and the chosen option differ, present the option as the best fit
   for that value and never write that they are equal. A choice the results ground by best fit or
   elimination may be presented even without numerical equality and without a calculation that
   produces the chosen value: do not re-validate it with stricter standards than the approval
   applied, and do not drop or replace it for lack of exactness.
4. **Identifiers.** An identifier you write must label the very object the results determined:
   the letter and text of an option, the number of a test, the name of an entity, a product code, a
   month or any other label. When the associations between identifiers and items are in the notes
   from the question, use them for a literal check: find the item the results determined and copy the
   identifier attached to it. Never take an identifier from the position of an item in a list, from
   the item's own number or from memory when the association does not establish it.
5. **Literal pairing is not analytical selection.** Pairing an approved object with the identifier
   that literally labels it, translating and formatting are presentation. You must not choose the
   option closest to a value when the results did not make that comparison, complete a calculation,
   resolve a residual conflict between results or invent an identifier that neither the results nor
   the notes provide. Global approval does not authorize inventing information. If, exceptionally,
   the request requires an identifier that no available material associates with the determined
   item, present the approved content without guessing the identifier, and never present an internal
   error message as the answer.
6. **Coherent justification.** When the answer includes a justification, make sure every formula,
   comparison and explanation you present points in the same direction as the conclusion you state;
   if the wording you drafted contradicts the approved content, rewrite it from that content.

The check is internal: do not describe it in the answer, and do not mention stages, tasks, criteria,
learnings or other internal details of the process. Write only what the user asked for.

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
- Literal pairing: the results determine "sample 2 — iron" and the notes record the options
  `A) 1, B) 2, C) 3`. Valid: `B`, because the option whose text is "2" is B. Invalid: `A (2 — iron)`,
  which joins a letter to an object it does not label.
- Approved best fit: the results estimate about 8.4 cm and select `B) 8 cm` as the best fit,
  comparing it with the other options. Valid: "B) 8 cm, the best fit for the estimated 8.4 cm".
  Invalid: "8.4 cm is exactly 8 cm", and also invalid: refusing to present B because 8.4 differs
  from 8.
- Open question with translation: the results state "the north warehouse used 1.5 MWh in June,
  assuming two shifts per day"; the request asks for the answer in Portuguese. Valid: the same
  warehouse, 1,5 MWh, June and the two-shift hypothesis, in Portuguese. Invalid: dropping the
  hypothesis, changing the unit to kWh without converting the value, or naming another warehouse.
- Direction of a comparison: the results conclude that stock decreased in the east branch and
  increased in the west branch. Invalid: a justification that says the east branch gained stock
  while the conclusion says it lost stock.
- Missing analysis: the results give only a ratio between two distances and the request asks for a
  period. Invalid: computing the period here or picking the option nearest to the ratio; that gap
  belongs to the global verification and additional planning, not to the presentation.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"final_answer": "markdown of the answer to the user"}
