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

Resolve the stated analytical objective, using prior findings from Key Learnings when needed.
Logical dependence does not widen scope. When this task owns the final determination, perform the
last calculation, integration or comparison it requires, including a supported comparative choice.
Limit other analysis to this task's goal; do not anticipate conclusions of other tasks or invent
findings that are missing from memory. C.3 will present the supported result in the user's format.

Produce only what this task asks for, satisfying each of the listed acceptance criteria. When this
task depends on values, quantities or conclusions obtained in previous steps, use the facts recorded
in **Key Learnings**. If the task description or some acceptance criterion cites a value estimated
during planning that diverges from the literal data of the question or from the value actually
calculated in **Key Learnings**, perform the calculation with the real values and explicitly record
the divergence in the justification, without forcing a mathematically incorrect calculation.
The same evidence rule applies to a qualitative premise or an unverified hypothesis introduced
during planning: establish the conditions and explain any conflict with the available facts rather
than forcing the prescribed conclusion. For an explicitly corrective task, investigate the named
conflict without presuming which earlier account is wrong.
When the task involves evaluating or comparing statements or options against a text, evaluate by
**best relative fit (elimination)**: distinguish serious contradictions or extrapolations from
paraphrases, syntheses and reasonable inferences, without discarding every option by requiring a
100% literal word-for-word match.
When the task asks for a selection, make the choice justified by the comparison. A supported
approximation or closest-value choice is valid when consistent with the data, applicable model and
precision; explain the approximation and any relevant difference. Do not invent a numerical
tolerance: selecting an option alone does not establish correctness. If a discrepancy remains
unsupported, explain the concrete limitation rather than assert an arbitrary choice.
The resolution goes in the `result` field, in markdown, with the result and its explanation even
when the final answer must be short or contain only a letter. For calculations, show formulas,
substitution with units, applicability, conventions and justified approximations; for interpretations
or choices, show the supporting evidence and reasoning.

In the `conclusion` field, write **only the final conclusion** of the resolution, in one or a few
self-sufficient sentences: the result obtained (with value and unit of measurement, when there is
one) or the statement the task arrived at, without intermediate formulas, steps or justifications.
The conclusion must be identical, in content, to the conclusion presented in `result` — for
example: "The average speed over the route is 20 m/s."

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"task_id": "...", "result": "markdown with the resolution", "conclusion": "final conclusion, without the reasoning"}
