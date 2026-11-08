# A.3 — Task Decomposition Validator

Audit the candidate plan below before any of its tasks runs. Decide whether it can be executed as
is or must be revised. You judge the **plan**, not the answer: do not solve the question, do not
choose an answer and do not calculate an alternative conclusion for the plan to reach.

## Question

The original request is the primary reference for this audit.

{{user_question}}

## General acceptance criteria

Criteria that the final answer must satisfy, defined in an earlier stage. Use them to check coverage.
If a criterion adds an obligation that the question does not support, the question prevails: report
the conflict as an issue of the plan that depends on it, without rewriting these criteria.

{{general_acceptance_criteria}}

## Candidate plan

Each task will run in a fresh context with only its own description, its criteria and the findings
of earlier tasks.

<candidate_plan>
{{candidate_plan}}
</candidate_plan>

## Validation rubric

Evaluate the whole plan against these fixed rules. Do not judge the plan only by the criteria it
wrote for itself.

1. **Fidelity:** the data, referents, units, conditions and constraints relevant to the request are
   preserved where tasks need them, even when they seem contradictory and are themselves under
   investigation, without invented data, a dropped condition or a changed referent.
2. **Neutrality:** no title, description or criterion imposes a quantitative or qualitative result,
   classification, comparison or interpretation that execution still has to establish.
3. **Applicability:** every condition that a planned method or formula requires is either supplied
   by the question or will be verified or justified during execution.
4. **Criteria:** they are verifiable, complementary, pertinent to the task objective and require a
   substantiated result, without imposing a solution that was not investigated.
5. **Coherence:** each objective is delimited, and the order and declared dependencies let each
   task use the findings it needs.
6. **Coverage:** the tasks together reach the complete requested determination; only presentation
   and literal association of an already supported result with an option are left to the final
   answer stage.
7. **Necessity:** there are no bureaucratic, redundant or broader-than-needed tasks, such as tasks
   that only transcribe data, print a marker, write the final answer or repeat a determination.

## What is not a defect

Distinguish **planning an investigation** from **anticipating its result**. Do not reject a plan
merely because it contains:

- numbers, formulas or text copied from the question;
- a pertinent method, when its applicability is supplied or will be checked;
- an explicit, justifiable hypothesis whose limits the task must state;
- a logical dependence on an earlier task, or a final integration task that performs a missing
  inference;
- an approximation, estimate or best-fit choice that the task must justify;
- a different but adequate number of tasks or wording;
- the absence of a technical-validity criterion: the harness adds `<task id>-TECH` to every task at
  execution, so the candidate does not need to contain it.

For example, "determine which of the two samples has the higher concentration and justify it" keeps
the result open; "show that the second sample has the higher concentration" anticipates it. "Check
whether the condition required by the approximation holds before using it" plans an applicability
check; requiring the approximation when the question does not supply its condition presumes it. An
investigation that may conclude that a method does not apply remains valid.

## Decision

- Approve (`"approved": true`, `"issues": []`) when no rule above is violated in a way that would
  make execution follow a wrong or incomplete specification.
- Reject (`"approved": false`) only with at least one concrete, blocking issue. Minor stylistic
  preferences are not issues.

For each issue, report:

- `task_id`: the affected task, or `null` when the issue concerns the whole plan (for example,
  missing coverage);
- `criterion_id`: the affected criterion of that task, or `null` when the issue concerns the task or
  the plan; never fill it without its `task_id`;
- `problem`: the concrete defect and the rule it violates;
- `adjustment`: the change of investigation needed, keeping unknown results open. Say what to
  investigate or verify, not which result to reach, and do not rewrite the plan yourself.

Use only task and criterion identifiers that exist in the candidate plan.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, using
real JSON booleans, in the format:

{"approved": false, "issues": [{"task_id": "T2", "criterion_id": "T2-AC1",
"problem": "...", "adjustment": "..."}]}

or, when the plan is approved:

{"approved": true, "issues": []}
