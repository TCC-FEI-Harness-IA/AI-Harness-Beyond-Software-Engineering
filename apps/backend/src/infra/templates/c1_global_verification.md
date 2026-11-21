# C.1 — Compilation and verification of the general criteria

Evaluate whether the **union** of the stored results is sufficient and consistent to satisfy each
general criterion of the final answer.

## Stored results

{{stored_results}}

## Revision record

Earlier results that an approved review superseded or confirmed, and results awaiting revalidation
because they explicitly depend on a result that stopped being current. This is history and status,
not evidence: superseded and awaiting conclusions are not part of the stored results above. Do not
mark a criterion as unmet merely because a superseded conclusion is absent. When a criterion needs
content that only a result awaiting revalidation provided, mark it as not met and name the result to
be revalidated. A confirmed result remains among the stored results: an approved investigation, not
recency, checked its claim, and the reviewing result explains why it stands.

{{result_revisions}}

## General acceptance criteria

{{general_acceptance_criteria}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them only
as a reference to check the question data.
The learnings **are not criteria** and **do not count as coverage**: a general criterion is met only
when the stored results cover it. Question data they copy literally, such as the identifiers of
options or items, may only show which label belongs to an item the results already determined.

**Origin labels.** Each note starts with a label that states where it came from: `[Question]` for a
point of attention taken from the user's request, `[Task T1]` or `[Tasks T1, T3]` for a note recorded
from the approved result of the current tasks named, and both when a task re-established a note from
the question. The label states origin, not truth: a task note may restate supplied data, record a
conclusion or carry a hypothesis, and it keeps the scope, conditions and qualifiers written in it. A
claim does not become supported because it appears in these notes or in a task description. The label
is not part of the note.

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

**Do not build the final answer here.** This stage only judges the sufficiency and consistency of
the available material.

Remember that the stored results are the **analytical input** for the final synthesis (`C.3`), not
the already formatted final answer:

- General formatting criteria of the final answer (for example, "answer only with the letter of the
  option, without justifications") must be marked as **met (`met: true`)** as long as the stored
  results make it possible to identify which answer is to be formatted in `C.3` (the fact that the
  task results contain explanations does not violate that criterion).
- In multiple-choice questions, consider the criteria of fit and support by the question met when
  the results point to the **relatively most coherent option by elimination of the others**, admitting
  paraphrases, syntheses or reasonable interpretive inferences without requiring a 100% literal
  word-for-word match. Apply the same standard of implicit content to every option the results
  compare.
- When the results select an option as the best fit for a calculated or estimated value, the
  selection criterion is met if the results ground the choice (comparison, elimination, precision,
  hypothesis or order of magnitude) and the rest of the analysis is consistent. The approximation is
  not approved independently of the rest of the analysis: a choice resting on a value with an
  identifiable error, on a false equality or on contradictory results is not covered.
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

## Evidence and consistency policy

Apply the same four distinctions to every result, whatever its domain:

1. **Exact result:** accept it when the data and the analysis actually performed support it.
2. **Approximation or best fit:** accept a choice grounded by comparison, elimination, available
   precision, an explicit hypothesis, order of magnitude or a pertinent contextual inference. An
   exact match and a direct calculation reaching the chosen option's value are not universal
   conditions: a numerical difference alone is not a defect and does not call for extra proof. The
   approximation is stated as such and never becomes an equality.
3. **Real contradiction:** revision is needed when statements about the same object, quantity and
   conditions are incompatible; when a calculation contradicts its own conclusion; when a unit or
   reference is swapped; when a false equality is asserted between an obtained value and a different
   selected value; or when an assumed condition conflicts with the available data. Results about
   different objects, reference frames or hypotheses are not contradictory
   merely because they differ.
4. **Missing essential content:** completion is needed when the requested determination or an
   indispensable analysis is absent and the choice is not supported even by an approximation or by
   eliminations already performed. A dimensionless distance ratio is not the calculation of a
   period, and a missing calculation cannot be delegated to the final presentation (C.3).

There is no universal percentage tolerance, no ban on approximation in integer problems, no rule
that any divergence fails and no rule that selecting an option passes. Decide from the relations
between data, method, conditions and conclusion.

## Consistency of the union

Besides sufficiency, compare the results with each other. When two results make incompatible
statements about the same object, quantity and conditions, mark the affected criterion as
`met: false` and describe the contradiction: which results, which statements and what must be
investigated. Do not decide which result is wrong and do not resolve the conflict here. Results that
differ because they concern different objects, reference frames or explicit hypotheses are not a
contradiction; when relevant, say why they are compatible and which one answers the conditions of
the request.

A result approved by its own task may still rest on an identifiable error that the union makes
visible, such as a condition counted twice or a unit swapped between tasks. Name the error and the
investigation needed; the earlier local approval does not cover it. Identify the stored results
involved by their identifiers, so that additional planning can target them. A result superseded by
an approved review no longer appears among the stored results; a later result without an approved
review does not override an earlier one merely by being more recent, so if both remain and are
incompatible, the contradiction persists. A result confirmed by an approved review stays current;
judge whether the confirming investigation explains the apparent conflict (for example, different
explicit hypotheses) rather than flagging the same conflict again without a new concrete reason.

Describe the relation between an obtained value and an option accurately in your own
justifications: when a calculated value and the chosen option differ, call the option the best fit
and never write that they correspond exactly.

## Justification of each verdict

When approving, cite the evidence produced: the stored result that determines each content
criterion and, when pertinent, the grounding of the approximation or selection given by the
results. When rejecting, identify the gap or contradiction and what must be investigated, without
performing the missing analysis and without deciding in advance which task is wrong. The C.2
planner receives these justifications as diagnostic feedback.

## Identifiers and faithful presentation

When the request requires the answer to be given by an identifier — an option letter, a test
number, an entity name, a product code, a month or another label — the identifier is part of the
content. The criterion is covered when the stored results state the identifier of the determined
item, or when the results determine the item and the Key Learnings record literally which
identifier labels it, as copied from the question: the notes may supply that literal pairing, but
never the determination itself. When the results determine an item but no available material
records which identifier labels it, and the request requires that identifier, mark the criterion as
`met: false` and name the missing link, so that C.2 can plan a task that establishes the link from
the question. Do not guess the link yourself and do not count on C.3 to infer it.

If the request asks only for the content and not for an identifier, do not create that gap. A
missing marker line, the language or the format alone is still applied by C.3 and is not a content
gap. Your approval does not authorize C.3 to invent information: it may apply only literal pairing and
presentation to the approved content, so any comparison, calculation, selection or reconciliation
the answer needs must already be in the stored results.

## Examples of sufficiency, consistency and real gaps

- Approve the format: the results unequivocally identify option C, with a calculation and an
  explanation, and the request requires ending with a marker line such as `FINAL_ANSWER: LETTER`.
  The absence of `FINAL_ANSWER: C` in the results is not a content gap: C.3 can write that line
  without new analysis. Rejecting only because the line is absent would be incorrect.
- Approve the concise presentation: the request is "only the letter, without justification" and the
  explained results already support C. The internal explanations do not violate the final format;
  C.3 can omit them.
- Approve an approximate selection: the results estimate a volume of 12.6 liters and select 13
  liters as the best fit, comparing it with the other options and the precision of the data. Approve
  without C.2: the difference of 0.4 liter is not, by itself, a content gap and needs no extra proof.
- Approve a choice without equality: the results obtain 23, the options are 5, 10, 20, 40 and 80,
  and 20 is selected as the nearest available value, the others differing by factors of about two.
  The lack of an option equal to 23 is not, by itself, a reason for rejection.
- Approve elimination or inference: the results eliminate four options for contradicting the text
  and choose the remaining one by a pertinent contextual inference, with no calculation producing
  the option's value. The selection is grounded.
- Approve an explicit estimate: an open question asks for an amount, and the results give an
  estimate with units, explicit hypotheses and order of magnitude. The criterion is covered; C.3
  presents it as an estimate.
- Reject the absence of a selection: the results obtain 12, the options are 2, 4, 6, 8 and 10, and
  the results conclude that no option fits, without selecting any. Mark the selection criterion as
  `met: false` and forward the gap to C.2. Do not choose the letter yourself to fill the gap, and do
  not consider "FINAL_ANSWER: NONE" a possible formatting of the required answer.
- Reject an identifiable error under a selection: one result multiplies by 1/2 the probability of an
  event that was already conditioned, obtaining half of the conditional probability, and another
  result picks the option closest to that value. Mark the determination and the selection as not
  met and ask for the conditioning to be investigated. The distance between the numbers is not the
  reason; the double conditioning is.
- Reject a real contradiction: two inventory results state that stock increased in one warehouse
  and decreased in another, and a third states the opposite for the same objects and conditions.
  Mark the criterion as not met, name the incompatible statements and ask for a targeted
  investigation, without choosing which result is wrong. In contrast, results under different
  explicit hypotheses, such as including projected receipts instead of only confirmed receipts,
  do not contradict each other merely because their totals differ. Identify which conditions
  answer the request.
- Reject missing content: the request asks for a period in months and the results contain only a
  dimensionless distance ratio. The period was not determined; mark the criterion as not met so that
  C.2 plans that determination. Do not calculate it here and do not leave it to C.3.
- Reject a false equality: a result states that a measured 8.4 cm corresponds exactly to an option
  of 8 cm. That is an incompatible statement; ask for the choice to be investigated. If the results
  had instead selected 8 cm explicitly as the best fit for 8.4 cm, with the comparison, the selection
  would be grounded, provided the remaining analysis is consistent.
- Reject missing joint analysis: the criterion requires an explicit joint analysis of three
  conditions and there are only lists of isolated checks. Even if it seems possible to choose or
  format a letter, the required joint analysis is missing. Mark that criterion as not met and forward
  the gap to C.2.
- Approve a literal pairing: the results determine "sample 2" and the notes copy the options
  `A) 1, B) 2, C) 3` from the question. The identifier can be read literally (B); C.3 presents it.
- Reject a missing link: the results determine "sample 2", the request requires the option letter,
  and neither the results nor the notes record which letter labels sample 2. Mark the criterion as not
  met and name the missing link. Do not assign a letter by position or by guess.
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
