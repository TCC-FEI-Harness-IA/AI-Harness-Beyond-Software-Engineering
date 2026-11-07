# B.1 — Task resolution

Solve **only** the task described below.

## Task

{{task_description}}

## Acceptance criteria for this task

{{task_acceptance_criteria}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them as
supporting context — for example, to check options, values and units of measurement —, without
widening the scope of this task.

{{learnings}}

## Previous attempts at this task

When this task has already been attempted and rejected, the previous attempts and the validator's
verdicts appear below, delimited by `<previous_attempts>`. They are the feedback for this new
attempt: fix exactly the criteria that were not met, without repeating what was rejected. This is a
new and complete resolution of the task, not the continuation of a previous conversation.

{{previous_attempts}}

## Instructions

Strict scope limit:

- **Do not** solve the final question of which this task is a part.
- **Do not** evaluate conditions that belong to other tasks.
- **Do not** anticipate conclusions that depend on results you do not have.

Produce only what this task asks for, satisfying each of the listed acceptance criteria. When this
task depends on values, quantities or conclusions obtained in previous steps, use the facts recorded
in **Key Learnings**. If the task description or some acceptance criterion cites a value estimated
during planning that diverges from the literal data of the question or from the value actually
calculated in **Key Learnings**, perform the calculation with the real values and explicitly record
the divergence in the justification, without forcing a mathematically incorrect calculation.
When the task involves evaluating or comparing statements or options against a text, evaluate by
**best relative fit (elimination)**: distinguish serious contradictions or extrapolations from
paraphrases, syntheses and reasonable inferences, without discarding every option by requiring a
100% literal word-for-word match.
When the task asks for the selection of an option and none coincides exactly with the value or
conclusion obtained, **explicitly select** the option with the closest value or the best fit and
record the observed difference. An approximation is a valid answer; concluding that "no option is
correct" or leaving the selection open is not.
The resolution goes in the `result` field, in markdown.

In the `conclusion` field, write **only the final conclusion** of the resolution, in one or a few
self-sufficient sentences: the result obtained (with value and unit of measurement, when there is
one) or the statement the task arrived at, without intermediate formulas, steps or justifications.
The conclusion must be identical, in content, to the conclusion presented in `result` — for
example: "The average speed over the route is 20 m/s."

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"task_id": "...", "result": "markdown with the resolution", "conclusion": "final conclusion, without the reasoning"}
