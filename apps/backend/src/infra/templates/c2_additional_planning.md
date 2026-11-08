# C.2 — Additional planning

Plan investigations only for the concrete content gaps identified by global verification. Do not
perform the new investigations during planning.

## Original Prompt

The user's original request is the source of literal question data: values with units of
measurement, excerpts, options when supplied, formulas, conditions and distance references.

{{user_question}}

## General criteria not yet met

{{unmet_criteria}}

## Global verification feedback

The C.1 report identifies the missing content or concrete inconsistency. It is diagnostic feedback,
not an approved result or a new source of question data. Use its justifications to target the gap;
do not promote a proposed correction to a proven conclusion.

{{global_verification_feedback}}

## Results already stored

For each current result — approved and neither superseded nor awaiting revalidation —
its statement and the conclusion it reached. The reasoning that led to each conclusion was omitted.

{{stored_results}}

## Revision record

Results superseded by approved reviews (history, not inputs), results confirmed by approved reviews
and results awaiting revalidation because they explicitly depend on a result that stopped being
current. A result awaiting revalidation is not a current input; it may be the target of a review
that confirms or replaces it. A confirmed result remains current because an approved investigation
checked it, not because of recency: do not plan another review of the same claim unless the
feedback gives a new concrete reason.

{{result_revisions}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by completed tasks, in order. Use them to identify available inputs and preserve
the data relevant to each new objective, checking literal question data against the Original Prompt.

{{learnings}}

## Content gaps and corrective investigation

Use already obtained results as inputs, distinguishing them from new conclusions still to obtain.
Avoid redoing an established investigation without a reason. When global verification identifies
a concrete contradiction or error, plan a targeted investigation of that issue, including relevant
prior claims and literal data. Do not decide which conclusion is wrong before executing the new
task. Approval of an earlier result does not prohibit investigating a specific defect flagged by
C.1: a previously approved result may be investigated when the feedback gives a concrete reason,
such as a conditioning error, a false equality or a statement incompatible with another result.
Plan that investigation as a reviewing task (see the `review` field below): the new task explains
its result and states which prior claim it confirms or corrects, as an explicit verdict that is
verified before it takes effect. Do not reopen unrelated resolved work or rewrite the received
general criteria.

The investigation must address the defect itself. A task that would only "choose the closest option"
to a value already flagged as wrong would cover the known defect and is not a valid investigation;
nor is a task that only prints the final line. When the gap is a missing determination, such as a
period in months when only a distance ratio exists, plan the explained determination itself.

Final language, format or conciseness alone are not content gaps: writing the final answer,
printing a marker or removing internal explanations belongs to C.3. If the analysis already supports
option C and only `FINAL_ANSWER: C` is missing, no writing-only task is needed. If a joint analysis
or comparative identification is missing, plan that explained investigation rather than just a
final line.

## Evidence and investigation

- **Literal data:** preserve the relevant values with units, excerpts, formulas, conditions and
  references supplied in the Original Prompt. Keep them distinct from recorded analytical claims.
- **Method:** a pertinent law or comparison procedure may be proposed, such as conservation of
  energy. Establish its applicability during execution rather than prescribing a result.
- **Hypothesis:** ask the task to verify any unestablished condition needed by a relation, or to
  justify an explicit assumption and its limits. A convenient physical regime or optical viewing
  condition is not automatically a supplied fact.
- **Result:** approved findings may be cited as existing inputs. Never pre-calculate the new task's
  values, qualitative conclusions, classifications, rankings or interpretations in a title,
  description or criterion. This includes substitutions and formulas dependent on an unverified
  hypothesis. When another new task needs a finding from an earlier new investigation, refer to
  **Key Learnings** and do not guess its content.

For example, investigate the source of transferred energy using the given processes and stored
claims without requiring that either claim be confirmed. Preserve the requested optical quantity
and distance references; establish conditions needed by the imaging relation instead of assuming
an image at infinity.

## Task scope and criteria

1. **Single goal permits logical dependence.** A task may consume prior findings through Key
   Learnings while retaining a clear objective, and declares the tasks that produce them in
   `depends_on`. Order new tasks so their dependencies are obtained before use. Preserve the literal data, references and existing findings relevant to each goal.
2. **Fresh context preserves explicit memory.** The solver receives its own description, criteria
   and accumulated Key Learnings, not the original conversation or complete prior resolutions.
   Each description must be self-sufficient for its objective and name any finding to retrieve
   from memory. Do not silently substitute planning guesses for missing findings.
3. Give each task its own verifiable criteria with identifiers such as `T4-AC1`. Criteria must be
   **complementary, never mutually exclusive**: one answer must be able to meet all of them at the
   same time. Check them in pairs: "answer only the option" conflicts with explaining the internal
   result. State which determination to establish and justify rather than fixing the new answer.
4. Use **affirmative and delimiting** scope, for example: "the investigation is restricted
   exclusively to the conflicting energy-source accounts and their justification." Restrict
   analytical actions outside the objective; do not impose arbitrary word bans. "Do not calculate
   the mass per spoon" limits analysis; "do not mention spoons" bans a contextual reference.
5. A task owning the **final determination** may perform the last calculation, integration or
   comparison needed by the request, including an explained comparative choice. Scope must permit
   its own goal. C.3 handles presentation and literal pairing of a supported result with an option
   label, without completing missing analysis.
6. Require the result **accompanied by the explanation** of why it is valid, **never the result
   alone**. In a calculation, require the formulas used, substitutions with units, conventions
   adopted (signs, reference frames, approximations) and justification of the steps. In a
   classification, interpretation or choice, require supporting evidence and reasoning. Write
   this in the description and include an acceptance criterion that checks it. A short final
   answer or an optional final justification does not remove the internal explanation requirement.
7. Permit supported paraphrases and contextual inferences; do not require a distractor's literal
   words or an unsupported conjunction of aspects. Compare options by best relative fit and
   elimination, without hyper-literalism. Allow a supported approximation or closest-value choice
   when justified by the data, model and precision, without inventing a numerical tolerance.
   Criteria must not demand exact coincidence or a direct calculation reaching the option's value
   as a universal condition, and an open question may be answered by an explained estimate.
   Selecting an option alone is not evidence of correctness. Investigate an unexplained discrepancy
   rather than require a convenient selection.

Plan only the investigations needed to fill the gaps; there is no preferred task count. Keep
criteria concise, and avoid tasks merely to transcribe data or restate already supported results.

## Reviewing stored results and declaring dependencies

Two optional structured fields connect a new task to stored results. They are the only way the
session changes which results are current; titles and descriptions never do.

- `review`: use it only when global verification gives a concrete reason to investigate specific
  stored results (a contradiction between results, a defective calculation or a missing grounding),
  or to revalidate a result awaiting revalidation. Give `task_ids`, the stored results whose claims
  are investigated (current or awaiting revalidation), and `reason`, the concrete defect taken from
  the feedback. The task receives those results' statements and conclusions and must return a
  verdict for each: `confirmed` or `superseded`. Do not decide the verdict in planning. Do not list
  results that merely differ, rest on other hypotheses or are unrelated to the gap. Each result is
  reviewed by at most one task of the batch; a task cannot review itself or another new task, and a
  superseded result cannot be reviewed again.
- `depends_on`: list the tasks whose findings this task explicitly uses as inputs, either current
  stored results or earlier tasks of this batch, whether or not the task reviews anything. If a
  listed result is later superseded, this task's result will await revalidation. Do not list a
  result that the same task reviews.

The two fields are independent; fill each one by its own rule. Include `review` only in a
reviewing task, as described above. Include `depends_on` in every task, reviewing or not, that uses
a finding of another task, and omit it only when the task uses no such finding. Using a stored
conclusion does not make a task a reviewing task: a task that builds on a stored result without
investigating it declares `depends_on` and omits `review`. A reviewing task automatically receives
the criterion `<task id>-REV`, which evaluates its verdicts; do not use that identifier yourself.

## Final plan review

Before returning the JSON, review the stored results together with the new plan within this
generation. Trace the unmet content obligations through the last task needed for the final
quantity or determination. If the request is a period in months and the stored result is only a
distance ratio, the new work must determine the period. Check that every gap, including a flagged
contradiction, has a targeted investigation, that data and references survive, dependencies use
actual findings, and criteria leave new conclusions open. Revise scopes that would forbid the
necessary final analysis. Leave only supported presentation and literal pairing to C.3.

This is an instruction within planning, not a separate phase or output field. Neither task count
nor JSON validity certifies semantic coverage; C.1 later judges the sufficiency of approved results.

**Batch limit:** the session holds at most {{max_tasks}} new tasks, a safety ceiling rather than a
target. Do not exceed this number and do not merge independent tasks into one just to fit. Keep
each objective clear. A batch above the limit is rejected for correction.

Continue numbering from `T{{next_task_number}}` to avoid collisions with existing task identifiers.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"tasks": [{"id": "T{{next_task_number}}", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T{{next_task_number}}-AC1", "description": "..."}],
"review": {"task_ids": ["..."], "reason": "..."}, "depends_on": ["..."]}]}

`review` and `depends_on` are optional and independent: omit `review` unless the task reviews stored
results; omit `depends_on` only when the task uses no finding of another task.
