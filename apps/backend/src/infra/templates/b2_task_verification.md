# B.2 — Verification of the task's acceptance criteria

Evaluate whether the preliminary result below meets the task's acceptance criteria.

## Preliminary result

{{preliminary_result}}

## Acceptance criteria for this task

{{task_acceptance_criteria}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them only
as a reference to check the data involved (options, values, units of measurement).
The learnings **are not criteria**: the evaluation remains restricted to the criteria of this task.

{{learnings}}

## Instructions

Go through the criteria **one by one**. For each criterion, decide whether it was met and write the
justification of the verdict. Then issue the final decision: `approved` only when **all** criteria
were met, `reproved` otherwise.

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

The evaluation is **local**: judge only the criteria of this task. Do not judge whether the result
answers the user's final question, do not judge the quality of the final answer and do not consider
anything beyond the criteria listed above. An intermediate task is not required to answer the whole
question: a partial result that its criteria ask for is complete for this task.

**Do not ignore, rewrite or waive any criterion received**, even if it seems poorly worded. The
interpretation of scope must follow the action the criterion restricts: citing a term as a
contextual reference is not the same as calculating another quantity, evaluating another condition
or anticipating a solution. If there is an explicit prohibition of words, it must also be checked as
it was received; this stage is not authorized to correct the planner's criteria.

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
