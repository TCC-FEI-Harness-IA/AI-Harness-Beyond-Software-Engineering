# C.2 — Additional planning

Create new independent tasks **only** to fill the content gaps pointed out below.

## Original Prompt

The user's original request, from which all tasks derive. It is the source of the literal data of
the question (options, values with units of measurement, formulas, conditions) that the new tasks
need.

{{user_question}}

## General criteria not yet met

{{unmet_criteria}}

## Results already stored

For each task already approved, its statement and the conclusion it reached. The reasoning that
led to each conclusion was omitted.

{{stored_results}}

## Key Learnings

Compact notes accumulated throughout the flow: the points of attention from the question and the
facts recorded by the tasks already completed, in the order in which they appeared. Use them to
write self-sufficient descriptions: copy into the description of each new task the question data it
needs (options, values with units of measurement, formulas, conditions), checking them against the
**Original Prompt**.

{{learnings}}

## Instructions

The new tasks exist to cover **only** the criteria not met. Do not create tasks that redo what is
already in the stored results and do not reopen what has already been verified.

Each task must:

1. Have **a single goal**, solvable independently of the others.
2. Carry **its own individual acceptance criteria**, which allow judging in isolation whether the
   task was solved well. The criteria of the same task must be **complementary, never mutually
   exclusive**: it must be possible for a single answer to meet all of them at the same time. Before
   closing the list, check the criteria in pairs and remove any contradiction — for example,
   "answer only the option" and "the answer must contain explanations" exclude each other and
   cannot coexist.
3. Include, among the criteria, **scope constraints that prevent the early resolution of the main
   question**, written in an **affirmative and delimiting** way — for example: "the scope of the
   answer is restricted exclusively to [task scope], without anticipating later steps or choosing
   the final option". Avoid phrasing the criterion with ambiguous negatives ("do not conclude
   whether...", "do not state that it is not...") that the verifier may misread when the task's own
   technical conclusion is an impossibility or a negation.
4. Require the task's answer to bring the **result accompanied by the explanation of why it is
   valid**, never the result alone. If the task involves a calculation, the answer must present the
   formulas used, the substitution of the values with units of measurement, the conventions adopted
   (signs, reference frames, approximations) and the justification of each step up to the final
   value; if it involves a classification or choice, it must present the reasoning that supports
   it. Write this requirement in the task description and include an acceptance criterion that
   checks it. Even when a pending general criterion asks for the final answer to the user to contain
   "only the letter of the option, without justification", **never** carry that format restriction
   over to the task: the concise formatting belongs exclusively to the final synthesis (`C.3`),
   while every task must make the justification of its result explicit to be verifiable.
5. **Never pre-calculate results of the new task in the acceptance criteria.** Do not solve the new
   task inside `description` or `acceptance_criteria` (`T*-AC*`), nor fix in advance the numeric
   value that the new task still has to calculate: rely only on the literal data of the **Original
   Prompt** and of **Key Learnings** and on the results already approved in **Results already
   stored**. Make sure that the last task of the plan concludes the calculation or the exact
   determination of the final quantity asked by the question, leaving only the presentation and the
   choice of the option letter to `C.3`.

Do not turn final language, format or conciseness into presentation tasks. The absence of a
formatted final line or the presence of internal explanations are not, by themselves, content gaps.
Use the pending criteria to identify which information is still missing, without rewriting or
revising them. Every new task still requires an explained result, even for a concise final answer.

## Examples of valid and invalid planning

- Real gap: a joint analysis is required, but there are only isolated checks. Valid: a
  self-sufficient task with the data already obtained, to determine and explain the intersection of
  the conditions. Invalid: asking only for a letter, forbidding the justification or forbidding the
  missing joint analysis.
- If option C is already supported and only a final line such as `FINAL_ANSWER: C` is missing,
  creating a task to write the line would be improper: C.3 applies the format. If identifying the
  option is what is missing, the task must produce the analysis and the explained identification,
  not just the final line.
- Valid for total mass: "do not calculate the mass per spoon". Invalid: "do not mention spoons".
  The contextual reference is allowed; performing the additional calculation is a real scope
  violation.
- "Be objective" does not authorize imposing two lines or a word limit. An optional justification
  in the final answer does not eliminate the mandatory explanation of the internal result.

In **multiple-choice questions** (especially when the previous results discarded all options due to
literal strictness), create a single comparative task that evaluates the options by **best relative
fit and elimination of the most serious distractors**, admitting paraphrases, syntheses or reasonable
interpretive inferences, without repeating hyper-literal prohibitions that make every option
unviable.

**Context will not be shared between tasks.** Each description must be self-sufficient.

**Batch limit:** the session holds at most {{max_tasks}} new tasks. Do not exceed this number and
do not merge independent tasks into one just to fit: keep each one autonomous and single-goal. A
batch above the limit is rejected and returned to you for correction.

Continue the task numbering from `T{{next_task_number}}`, so that the identifiers do not collide with
those of the existing tasks.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"tasks": [{"id": "T1", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}
