# B.2 — Verification of the task

Evaluate whether the preliminary result below accomplishes this task's objective on a valid technical
basis and meets every verification criterion listed for it.

## Task

The identification, title and description of the task being verified. The description explains the
scope and the objective of the task: it is not the result under evaluation and it is not an
additional set of criteria.

{{task_description}}

## Preliminary result

The resolution produced for this task. It is the object of the evaluation.

{{preliminary_result}}

## Acceptance criteria for this task

The effective verification criteria: the criteria written in planning, followed by the fixed
technical criterion `<task id>-TECH`, which the harness adds to every task, and, in a task that
reviews stored results, the revision criterion `<task id>-REV`. Evaluate every one of them.

{{task_acceptance_criteria}}

## Proposed revision

When the task investigates stored results, the solver's explicit revision proposal appears below:
for each result under review, its statement, the conclusion under review, the proposed verdict and
its justification. The revision criterion (`<task id>-REV`) listed above evaluates it. Otherwise this
area states that the task does not review stored results.

{{revision_proposal}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them only
as a reference to check the data involved (options, values, units of measurement).
The learnings **are not criteria**: the evaluation remains restricted to the criteria of this task.

{{learnings}}

## Instructions

Go through the criteria **one by one**. For each criterion, decide whether it was met and write the
justification of the verdict. Then issue the final decision: `approved` only when **all** criteria
were met, including `<task id>-TECH` and, when it is listed, `<task id>-REV`; `reproved` otherwise.

Report consistency rules, checked automatically — a report that violates them is rejected and
returned to you for correction:

- Make **exactly one evaluation for each criterion** listed above, using the exact identifier of
  the criterion in `criterion_id`. Do not omit any criterion. Do not repeat a criterion. Do not
  invent identifiers that are not in the list.
- Set `met` equal to `false` on every criterion not met and `true` on those met.
- `unmet_criteria_ids` must contain exactly the identifiers of the criteria with `met` equal to
  `false`, without repetitions. The list is empty only when the decision is `approved`.
- The decision is `approved` only when all criteria have `met` equal to `true`; a single criterion
  with `met` equal to `false` is enough for the decision to be `reproved`.

The evaluation is **local**: judge this task — its objective, described above, and the criteria
listed for it. Do not judge whether the result answers the user's final question, do not judge the
quality of the final answer and do not consider anything beyond this task's objective and criteria.
An intermediate task is not required to answer the whole question: a partial result that its
objective and criteria ask for is complete for this task.

Your role is to verify, not to solve: do not write the corrected resolution, do not complete a
missing step yourself and do not edit, add or remove criteria. When you find a concrete defect, mark
the affected criterion as not met and describe the defect, so that the solver can correct it in a
new attempt.

**Do not ignore, rewrite or waive any criterion received**, even if it seems poorly worded. The
interpretation of scope must follow the action the criterion restricts: citing a term as a
contextual reference is not the same as calculating another quantity, evaluating another condition
or anticipating a solution. If there is an explicit prohibition of words, it must also be checked as
it was received; this stage is not authorized to correct the planner's criteria. When a planned
criterion is infeasible or conflicts with the data of the task — a defect of planning —, evaluate it
as received and state the planning defect explicitly in its justification; this stage cannot send
the task back to planning nor waive the criterion.

Examples for a criterion "do not calculate the mass per spoon":

- Met: "The question mentions spoons; the total mass is 2 g + 4 g = 6 g". The mention is
  contextual, and the result is explained within the scope.
- Not met: "The total mass is 6 g; dividing by two spoons, that is 3 g per spoon". The additional
  calculation performs a forbidden action, even if it is correct.
- If the criterion received were "do not mention spoons", the first sentence would violate it.
  Do not replace that criterion with "do not calculate the mass per spoon" during the evaluation.

A well-founded conclusion about the task's own goal is not an undue anticipation. Solving
conditions outside the goal or announcing the global solution when the criterion forbids it is a
violation. Internal explanations must not be judged by the format of the final answer: a marker
line, an answer limited to a letter or the final language is not an internal obligation unless
such a restriction appears in the local criteria received; all of those remain mandatory.

## Technical validity criterion (`<task id>-TECH`)

This fixed criterion asks whether the result accomplishes **this task's objective** on a basis
compatible with the data, methods and conditions that apply. A result can meet every planned
criterion and still fail it — for example, when it follows the planned method exactly but the
method does not hold under the conditions of the task. It is independent of `<task id>-REV`: a
review may demonstrate its verdicts while another part of the result has a technical error, or be
technically sound without demonstrating the proposed verdicts; each criterion receives its own
verdict.

Check the analytical basis **before** accepting an approximation, an estimate, an elimination or a
best-fit choice:

1. **Premises:** each premise is supplied by the task or by **Key Learnings**, or it is explicitly
   justified. A supplied datum is not an inferred result; the absence of information does not
   demonstrate its negation; a convenient hypothesis does not become a fact without support.
2. **Referents and conditions:** values keep their referents, units, conditions and temporal stage.
3. **Method:** the method or relation applies under the stated conditions, and the contributions
   and conditions relevant to the analysis are taken into account.
4. **Support:** the steps actually support the conclusion; the presence of an explanation is not
   enough.
5. **Consistency:** calculation, text and conclusion agree with each other and with the available
   data.
6. **Approximations and hypotheses:** an approximation, hypothesis or best-fit choice has pertinent
   support.

Keep these distinctions:

- Narrative coherence does not establish attribution to a source. Do not invent a verifiable
  reference, and do not require an external lookup or a bibliographic citation when the task does
  not ask for one.
- Selecting the answer nearest to a value does not establish that the value came from a valid model:
  check the derivation first. When the derivation is wrong, the defect is the error, not the
  distance between the numbers.
- A hypothesis must be compatible with the scenario and justified; being conceivable or not forbidden
  is not enough to adopt it, least of all only for the candidate it favours. Apply the same standard
  of implicit content and of support to every hypothesis or option compared. Keep pertinent
  contextual inferences, without a literalism that rejects one option for omitting a word while
  accepting the same omission in another.
- Approximations, estimates, elimination and best fit remain valid when supported: there is no
  universal tolerance and no requirement to calculate directly up to every answer.
- Explicit constraints of the user, including a required precision or exactness, remain mandatory;
  an anticipation written by the planner is not an obligation of the user.

When simple and pertinent to the task, cross-check the result from another angle: the direction of
a variation, a limiting case, the compatibility between parts of the text, a temporal relation, a
referent or unit, or a consequence of a generalization. These are examples, not a mandatory list of
techniques for every task, and you do not need to produce a second complete solution.

`<task id>-TECH` covers only this task's objective. It does not demand analyses that belong to other
tasks, the final answer format, an external justification that was not requested or an exactness
incompatible with a supported estimate.

The justification of `<task id>-TECH` must point to the relevant datum or passage, the decisive
premise and the relation actually checked. Saying that the explanation is complete or restating its
conclusion is not a justification. When the criterion is not met, name the datum, relation,
hypothesis or step that fails and what the next attempt must investigate.

## Technical verification of the local criteria

Check the content, not only the presence of an explanation. The presence of an explanation is not
its correctness. For each criterion, verify that the formula or method applies under the stated
conditions, that the data and units used match the task and **Key Learnings**, that each step
follows from the previous one and that the conclusion follows from the calculation or analysis
shown. A criterion that asks for a correct, justified result is not met by a wrong derivation that
is fully written out: for example, a conditional probability that multiplies again by the
probability of an event already given by the condition is a conditioning error. Name the concrete
defect in the justification — the step, the relation or the datum affected — so that the next
attempt can correct it; do not perform the corrected resolution here.

If an acceptance criterion carries a number or expression improperly pre-calculated during planning
that diverges from the correct deduction from the question data and the **Key Learnings**, consider
the criterion **met (`met: true`)** when the result demonstrates and justifies the correct
calculation of that quantity. A planning anticipation is not the standard of correctness.

Avoid **hyper-literalism**: when a criterion requires an analysis, conclusion or option to be
supported by the text or question, consider the criterion **met** if the result demonstrates the
**best relative fit (by elimination of the most serious distractors)** or a coherent paraphrase and
interpretive inference, without requiring a 100% literal word-for-word match. Apply the same
standard of implicit content to every option compared: for example, a text describing residents
deliberating together may support an interpretation of collective decision-making without using
that exact term. Do not reject the supported interpretation for lacking a literal word while
accepting implicit content for another option.
Literal wording is required only when the criterion explicitly demands that wording. When a
justification is only less explicit than it could be, say what link is missing; do not treat that
as evidence that another option is better.

## Revision criterion

The revision criterion is met only when the preliminary result demonstrates every proposed verdict.
`superseded` requires the concrete error in the reviewed claim to be identified and the corrected
conclusion to be established by the analysis shown; `confirmed` requires the reviewed claim to
withstand the investigation. Recency, a different hypothesis, a different wording or a bare
assertion that the earlier result is wrong does not support `superseded`, and confirming an earlier
result is a valid outcome. Approving the task approves the proposal: an approved `superseded` result
stops being a current fact. Do not rewrite the proposal or substitute another verdict; when support
is missing, mark the criterion as not met and name what is missing.

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

## Selection criteria

When a criterion requires selecting the option that corresponds to the value or conclusion obtained
— even if worded as "matches exactly" or "the only one that coincides" —, it is met when the result
selects an option and grounds the choice under the policy above: an exact match, or a best fit
supported by comparison, elimination, precision, hypothesis, order of magnitude or contextual
inference, without asserting a false equality. The lack of an exact match is not, by itself, a
reason for rejection, and the choice does not need a direct calculation reaching the option's value.

Selecting the closest option to a value obtained through an identifiable error does not meet it:
the defect is the error, not the distance between the numbers. The criterion is also not met when
the result selects no option although one is required and states no concrete limitation, when it
creates a non-existent option, or when another available option is evidently better supported by
the result itself.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence,
filling `criteria_evaluation` first, `unmet_criteria_ids` next and `decision` last, in the format:

{"criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": [], "decision": "approved"}

Evaluate `<task id>-TECH` like any other criterion. For example, when the planned criterion is met
but the technical basis fails:

{"criteria_evaluation": [{"criterion_id": "T2-AC1", "met": true, "justification": "..."},
{"criterion_id": "T2-TECH", "met": false, "justification": "..."}],
"unmet_criteria_ids": ["T2-TECH"], "decision": "reproved"}
