# A.2 — Breakdown into single-goal tasks

Plan an ordered sequence of investigations that together determine what the question asks. Each
task has a **single responsibility**, a clear objective, the data it needs and verifiable criteria.
Plan the investigations; do not perform them here. The plan is a candidate: a separate validation
stage audits it before any task runs.

## Question

{{user_question}}

## Previous candidate and validation report

{{plan_revision}}

## Evidence and investigation

Keep these categories distinct in every title, description and acceptance criterion:

- **Literal data:** copy the relevant values with units, excerpts, formulas, conditions and
  references supplied by the question, keeping each value attached to its referent. These are not
  your findings.
- **Method:** a pertinent law, model or comparison procedure may be planned. Choosing a method is
  not pre-calculating a result. When the method depends on a condition not yet established, ask the
  task to establish its applicability during execution; do not presume it.
- **Hypothesis:** when a method requires an unestablished condition, ask the task to verify that
  condition or justify an explicit assumption and its limits. Never present a convenient condition
  as a supplied fact.
- **Result:** values, qualitative conclusions, classifications, comparisons, rankings and
  interpretations still to be obtained must remain open, including in titles and criteria. Do not
  pre-calculate them or require a specific one. For later tasks, name the finding needed from
  **Key Learnings**; do not guess what the preceding task will conclude.

For example, ask to determine which of two collisions has the greater average force and explain the
analysis, rather than require that one named collision have the greater force.

## Task scope and criteria

1. **Single goal permits logical dependence.** A task can consume a previous result from Key
   Learnings while having one clear analytical objective. Order the tasks so required findings are
   obtained before use.
2. **Fresh context is not absence of memory.** The solver receives its own task, criteria and the
   accumulated Key Learnings, not the original question or other tasks. Make each description
   self-sufficient for its objective: copy the relevant question content concisely and identify any
   previous finding it needs.
3. Give every task its own verifiable criteria, identified as `T1-AC1`, `T1-AC2`, etc. They must be
   **complementary, never mutually exclusive**: one answer must be able to meet all of them at the
   same time. For example, "answer only the option" conflicts with a requirement to explain the
   internal result. Criteria specify what to determine and how to substantiate it, not which
   as-yet unknown conclusion must be reached.
4. Express scope in an **affirmative and delimiting** way, for example: "the analysis is restricted
   exclusively to the average force comparison and its justification." Restrict actions outside the
   objective, not contextual words: "do not calculate the mass per spoon" delimits an action;
   "do not mention spoons" unnecessarily forbids a contextual reference. A negative technical finding
   can be a valid result within scope.
5. The task responsible for the **final determination** may perform the last calculation,
   integration or comparison necessary to answer the question, including an explained choice. C.3
   only presents an already supported result and pairs it literally with an option label.
6. Require the result **accompanied by the explanation** of why it is valid, **never the result
   alone**: for calculations, the formulas used, substitution with units, conventions adopted and
   justification of the steps; for an interpretation, classification or choice, the supporting
   evidence and reasoning. Write this in the description and include an acceptance criterion that
   checks it. Do not turn the user's final format (a letter, a short answer) into an internal
   obligation.
7. Interpretive criteria allow supported paraphrases and contextual inference; do not demand the
   literal words of a distractor or a 100% literal match. Comparative questions may be settled by
   best relative fit and elimination. A supported approximation or closest-value choice remains
   valid when justified by the data, model and precision; do not invent a numerical tolerance, and
   do not demand exact coincidence or a direct calculation reaching an option's value as a universal
   condition. An open question may be answered by an explained estimate. Selecting an option alone
   does not establish correctness.

## Declared dependencies

When a task uses a finding of an earlier task of this plan, list that task's identifier in the
optional `depends_on` field, for example `"depends_on": ["T1"]` in task T2. List only earlier tasks
of this plan, and omit the field when a task does not use another task's finding.

## Parsimony and coverage

Plan the **smallest possible number of tasks** that covers the request, without a preferred count.

- **Decompose by conditions or logical steps, never by option.** Keep the comparison of offered
  statements against a common question or condition in a single investigation.
- **Avoid bureaucratic or redundant tasks:** do not create tasks merely to transcribe data, print a
  marker, write the final answer or repeat a determination already made.
- The last task needed must reach the requested determination or final quantity; only presentation
  and the literal association of a supported result with an option are left to C.3.

**Batch limit:** the session holds at most {{max_tasks}} tasks, a safety ceiling rather than a
target. Do not exceed this number and do not merge genuinely independent tasks into one just to fit.
A batch above the limit is rejected for correction.

Number the tasks starting from `T1`.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"tasks": [{"id": "T1", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}

The `depends_on` field is optional: add it, for example `"depends_on": ["T1"]`, only to a task that
uses the finding of an earlier task of this plan, and omit it in the other tasks.
