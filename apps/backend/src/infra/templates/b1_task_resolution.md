# B.1 — Task resolution

Solve **only** the task described below.

## Task

{{task_description}}

## Acceptance criteria for this task

The criteria by which the validator will evaluate this resolution, one by one: the criteria written
in planning, the fixed technical criterion `<task id>-TECH`, which the harness adds to every task,
and, when this task reviews stored results, the revision criterion `<task id>-REV`. The task is
approved only when all of them are met.

{{task_acceptance_criteria}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them as
supporting context — for example, to check options, values and units of measurement —, without
widening the scope of this task.

{{learnings}}

## Results under review

When planning made this task a corrective investigation, the stored results it investigates appear
below, with the concrete reason for the investigation. They are claims to check, not established
facts. Otherwise this area states that the task does not review stored results.

{{results_under_review}}

## Previous attempts at this task

When this task has already been attempted and rejected, the previous attempts and the validator's
verdicts appear below, delimited by `<previous_attempts>`. They are the feedback for this new
attempt: address the concrete problem each verdict identifies in the criteria that were not met,
without repeating what was rejected. Keep a supported conclusion that the verdict did not refute:
when a verdict only notes that a term is implicit or worded differently, make the supporting link
explicit instead of switching to another conclusion. When a verdict demonstrates an error in data,
conditions or calculation, correct it. This is a new and complete resolution of the task, not the
continuation of a previous conversation.

{{previous_attempts}}

## Instructions

Resolve the stated analytical objective, using prior findings from Key Learnings when needed.
Logical dependence does not widen scope. When this task owns the final determination, perform the
last calculation, integration or comparison it requires, including a supported comparative choice.
Limit other analysis to this task's goal; do not anticipate conclusions of other tasks or invent
findings that are missing from memory. C.3 will present the supported result in the user's format.

Produce only what this task asks for, satisfying each of the listed acceptance criteria. When this
task depends on values, quantities or conclusions obtained in previous steps, use the facts recorded
in **Key Learnings**. Preserve literal inputs copied from the user's request, including values,
units, references and conditions; do not demote supplied data to assumptions merely because they
appear in the task. Distinguish them from planning-derived values, conclusions or unstated assumptions:
these are hypotheses to verify, not demonstrated truths. If a planning anticipation diverges from
the literal data of the question or from the value actually calculated in **Key Learnings**,
perform the calculation with the real values and explicitly record the divergence in the
justification, without forcing a mathematically incorrect calculation. The same evidence rule
applies to a qualitative premise or an unverified hypothesis introduced during planning: establish
the conditions and explain any conflict with the available facts rather than forcing the
prescribed conclusion. For an explicitly corrective task, investigate the named conflict without
presuming which earlier account is wrong.
When the task involves evaluating or comparing statements or options against a text, evaluate by
**best relative fit (elimination)**: distinguish serious contradictions or extrapolations from
paraphrases, syntheses and reasonable inferences, without discarding every option by requiring a
100% literal word-for-word match. Apply the same standard of implicit content to every option
compared.
When the task asks for a selection, make the choice justified by the comparison. A supported
approximation or best-fit choice is valid under the policy below; do not invent a numerical
tolerance, and selecting an option alone does not establish correctness.
The resolution goes in the `result` field, in markdown, with the result and its explanation even
when the final answer must be short or contain only a letter. For calculations, show formulas,
substitution with units, applicability, conventions and justified approximations; for interpretations
or choices, show the supporting evidence and reasoning.

## Investigating results under review

When results under review are listed above, investigate the named defect with the data, conditions
and method it requires, without presuming which account is wrong. Then give, in the `revision`
field, exactly one verdict for each result under review:

- `superseded` only when your investigation identifies the concrete error in that claim (a datum,
  condition, unit, reference or step) and establishes the corrected conclusion in `result`;
- `confirmed` when the claim withstands the investigation, including when an apparent conflict is
  explained by different objects, reference frames or hypotheses.

Recency, a different hypothesis or a different wording is not evidence of an error. Justify each
verdict with the specific finding, and explain in `result` what was checked and why each verdict
follows. A superseded result stops being current as a whole: restate in `result` any of its claims
that your investigation shows to remain valid. A `superseded` result stops being a current fact only
if the validator approves your investigation. When no result is under review, omit the `revision`
field: an ordinary task does not revise stored results, even when its conclusion differs from one of
them.

## Technical validity (`<task id>-TECH`)

Every task is also evaluated by the fixed criterion `<task id>-TECH`: the result must accomplish
this task's objective on a basis compatible with the data, methods and conditions that apply.
Meeting the planned criteria does not replace it, and following a planned method does not exempt
you from checking that it applies. Before choosing an approximation, an estimate or a best-fit
option, check the analytical basis:

- Use supplied data as supplied and justify any premise you add. A hypothesis is stated as a
  hypothesis, compatible with the scenario and justified, and never presented as a fact; the
  absence of information does not demonstrate its negation.
- Keep referents, units, conditions and temporal stage.
- Confirm that the method applies under the stated conditions and take into account the
  contributions and conditions relevant to the analysis.
- Make the steps actually support the conclusion, and keep calculation, text and conclusion
  consistent with each other.
- Do not attribute a claim to a source on narrative coherence alone, and do not invent a verifiable
  reference.
- Apply the same standard of support and implicit content to every hypothesis or option compared.

When simple and pertinent, cross-check the result from another angle — the direction of a variation,
a limiting case, the compatibility between parts of the text, a temporal relation, a referent or
unit. `<task id>-TECH` covers only this task's objective: it does not demand analyses of other
tasks, the final answer format or an exactness incompatible with a supported estimate.

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

## Calculated result and chosen option

Keep the **calculated or inferred result** distinct from the **selected option**. Report the value
you obtained with its unit and precision; when it differs from the option chosen, say that the
option is the best fit and why (comparison, elimination, precision, hypothesis or order of
magnitude), never that the two are equal. A choice may also rest on interpretation or elimination
without any calculation reaching the option's value. For an open question that admits an estimate,
give the value with units, the hypotheses adopted and their effect on precision, and label it as
an estimate.

Comparing options does not mask a calculation error. Before choosing the option nearest to a value,
check the derivation that produced it: conditions applied once, events counted once, units and
references. If the check reveals an identifiable error (for example, multiplying again by the
probability of an event already included in a conditional), correct the derivation rather than
choosing the option nearest to the wrong value. If a discrepancy remains unexplained after that
check, state the concrete limitation instead of asserting an arbitrary choice.

When the request or the task requires selecting an option, still select the supported one; the
obligation to select does not make the analysis correct by itself.

## Conclusion field

In the `conclusion` field, write **only the final conclusion** of the resolution, in one or a few
self-sufficient sentences: the result obtained (with value and unit of measurement, when there is
one) or the statement the task arrived at, without intermediate formulas, steps or justifications.
The conclusion must be identical, in content, to the conclusion presented in `result` — for
example: "The average speed over the route is 20 m/s." When an option was chosen by best fit, keep
both the obtained value and the chosen option, without stating that they are equal.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"task_id": "...", "result": "markdown with the resolution", "conclusion": "final conclusion, without the reasoning"}

Only when results under review are listed, add the `revision` field, with one verdict per result
under review, in the format:

{"task_id": "...", "result": "...", "conclusion": "...", "revision": [{"task_id": "id of a result
under review", "verdict": "confirmed or superseded", "justification": "..."}]}
