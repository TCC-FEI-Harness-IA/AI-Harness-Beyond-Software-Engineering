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
anything beyond the criteria listed above.

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
violation. Internal explanations must not be judged by the format of the final answer, unless such
a restriction appears in the local criteria received; all of them remain mandatory.

Avoid **hyper-literalism**: when a criterion requires an analysis, conclusion or option to be
supported by the text or question, consider the criterion **met** if the result demonstrates the
**best relative fit (by elimination of the most serious distractors)** or a coherent paraphrase and
interpretive inference, without requiring a 100% literal word-for-word match. Likewise, if an
acceptance criterion carries a number or expression improperly pre-calculated during planning that
diverges from the correct mathematical/physical deduction from the question data and the **Key
Learnings**, consider the criterion **met (`met: true`)** when the result demonstrates and justifies
the correct calculation of that quantity.

**Approximations in the selection of options are allowed.** When a criterion requires selecting the
option that corresponds to the value or conclusion obtained — even if worded as "matches exactly"
or "the only one that coincides" —, consider it **met (`met: true`)** if the result **explicitly
selects a single option** as the one with the closest value or the best fit, even if it records the
difference between the value obtained and the option's value. The lack of an exact match is not a
reason for rejection. The criterion is **not met** only when no option is selected, when the result
concludes "none" or creates a non-existent option, or when another available option is evidently
closer to the value obtained.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence,
filling `criteria_evaluation` first, `unmet_criteria_ids` next and `decision` last, in the format:

{"criteria_evaluation": [{"criterion_id": "...", "met": true,
"justification": "..."}], "unmet_criteria_ids": [], "decision": "approved"}
