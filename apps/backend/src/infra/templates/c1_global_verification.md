# C.1 — Compilation and verification of the general criteria

Evaluate whether the **union** of the stored results is sufficient to satisfy each general
criterion of the final answer.

## Stored results

{{stored_results}}

## General acceptance criteria

{{general_acceptance_criteria}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them only
as a reference to check the question data.
The learnings **are not criteria** and **do not count as coverage**: a general criterion is met only
when the stored results cover it.

{{learnings}}

## Instructions

The evaluation is **global**, not per task: consider the results together and decide, criterion by
criterion, whether what has already been produced is enough to satisfy it. Justify each verdict.

Issue `approved` only when **all** general criteria are covered, and `reproved` otherwise.

Report consistency rules, checked automatically — a report that violates them is rejected and
returned to you for correction:

- Make **exactly one evaluation for each general criterion** listed above, using the exact
  identifier of the criterion in `criterion_id`. Do not omit any criterion. Do not repeat a
  criterion. Do not invent identifiers that are not in the list.
- Set `met` equal to `false` on every criterion still uncovered and `true` on those covered.
- `unmet_criteria_ids` must contain exactly the identifiers of the criteria with `met` equal to
  `false`, without repetitions. The list is empty only when the decision is `approved`.
- The decision is `approved` only when all criteria have `met` equal to `true`; a single criterion
  with `met` equal to `false` is enough for the decision to be `reproved`.

**Do not build the final answer here.** This stage only judges the sufficiency of the available
material.

Remember that the stored results are the **analytical input** for the final synthesis (`C.3`), not
the already formatted final answer:

- General formatting criteria of the final answer (for example, "answer only with the letter of the
  option, without justifications") must be marked as **met (`met: true`)** as long as the stored
  results make it possible to identify which answer is to be formatted in `C.3` (the fact that the
  task results contain explanations does not violate that criterion).
- In multiple-choice questions, consider the criteria of fit and support by the question met when
  the results point to the **relatively most coherent option by elimination of the others**, admitting
  paraphrases, syntheses or reasonable interpretive inferences without requiring a 100% literal
  word-for-word match. Likewise, when the results explicitly select the option whose value is
  closest to the calculated one, consider the selection criteria met: approximations are allowed as
  long as an option is chosen.
- Check whether the stored results concluded **up to the last logical step or final calculation
  asked by the question** (for example: if the question asks for the *month following* an
  overtaking, or the *additional quantity* to be added, it is not enough to have only the overtaking
  month or the initial quantity; if that final determination is missing from the stored results,
  mark the corresponding criterion as `met: false` so that the additional planning creates the final
  task).

For language, format and presentation constraints, judge whether C.3 can apply them to the approved
content without new analytical reasoning. Do not require each intermediate result to already be the
final answer. Stored results written in a language other than the one required for the final answer
do not make a language criterion unmet: C.3 writes the answer in the required language. When
justifying `met: true`, indicate the content that allows the requested presentation.

For content requirements, identify the evidence in the stored results. The possibility of
formatting an answer does not make up for missing analysis, calculation or grounding. Do not perform
here the missing analysis and then declare it covered; the gap must go on to C.2. The learnings
remain a separate reference and do not replace that evidence.

## Examples of sufficiency and real gaps

- Approve the format: the results unequivocally identify option C, with a calculation and an
  explanation, and the request requires ending with a marker line such as `FINAL_ANSWER: LETTER`.
  The absence of `FINAL_ANSWER: C` in the results is not a content gap: C.3 can write that line
  without new analysis. Rejecting only because the line is absent would be incorrect.
- Approve the concise presentation: the request is "only the letter, without justification" and the
  explained results already support C. The internal explanations do not violate the final format;
  C.3 can omit them.
- Approve an approximate selection: the results obtain 23, the options are 1, 4, 20, 1 and 2, and
  within the tasks 20 is selected as the closest. The selection criterion is met; the approximation
  difference is not a content gap.
- Reject the absence of a selection: the results obtain 12, the options are 2, 4, 6, 8 and 10, and
  the results conclude that no option fits, without selecting any. Mark the selection criterion as
  `met: false` and forward the gap to C.2. Do not choose the letter yourself to fill the gap, and do
  not consider "FINAL_ANSWER: NONE" a possible formatting of the required answer.
- Reject missing content: the criterion requires an explicit joint analysis of three conditions
  and there are only lists of isolated checks. Even if it seems possible to choose or format a
  letter, the required joint analysis is missing. Mark that criterion as not met and forward the gap
  to C.2.
- Optional justification: the lack of an explanation aimed at the user is not, by itself, a pending
  item if the request allows it without requiring it and the conclusion is already supported.
  Mandatory justification: if the request requires grounding and it is not in the results, reject
  the corresponding criterion. Do not invent that requirement when the request only asks for
  objectivity.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence,
filling `criteria_evaluation` first, `unmet_criteria_ids` next and `decision` last, in the format:

{"criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": [], "decision": "approved"}
