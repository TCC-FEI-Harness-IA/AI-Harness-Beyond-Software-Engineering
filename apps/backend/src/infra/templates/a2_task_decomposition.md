# A.2 — Breakdown into single-goal tasks

Break the question below into autonomous tasks, each with a **single responsibility**.

## Question

{{user_question}}

## Instructions

Each task must:

1. Have **a single goal**, solvable independently of the others.
2. Carry **its own individual acceptance criteria**, which allow judging in isolation whether the
   task was solved well. The criteria identifiers follow the form `T1-AC1`. The criteria of the same
   task must be **complementary, never mutually exclusive**: it must be possible for a single answer
   to meet all of them at the same time. Before closing the list, check the criteria in pairs and
   remove any contradiction — for example, "answer only the option" and "the answer must contain
   explanations" exclude each other and cannot coexist.
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
   checks it.
5. **Never pre-calculate results or anticipate calculations in the planning.** This stage is
   planning only: **do not solve the problem here**. It is forbidden to include numeric values
   calculated by you, intermediate results, ready-made algebraic substitutions or answer keys in the
   `description` or `acceptance_criteria` (`T*-AC*`) fields. The acceptance criteria must describe
   **which** quantity, relation or property must be determined and justified (for example,
   "Determines the numeric value of the resultant force with its SI unit"), and **never** fix in
   advance what it should be worth (for example, never write "Obtains a force equal to 15 N" or
   "Substitutes x = 4"). Likewise, in the following tasks (`T2`, `T3`...), **never try to guess or
   fill in the result that the previous task will find**: copy only the relevant raw data from the
   original question and instruct the task to use the value or conclusion recorded by the previous
   tasks in the **Key Learnings**.

**Context will not be shared between tasks.** Each task will be executed in isolation, with no
access to the original question, to the other tasks or to their results. Therefore the description
of each task must be self-sufficient: everything needed to solve it must be written in it, but
concisely — include only the data, excerpts or conditions relevant to that task, without needlessly
copying the whole question over and over.

## Parsimony and efficiency guidelines

Plan **the smallest possible number of tasks** able to produce the necessary inputs (typically
**2 to 4 tasks**). Decompose parsimoniously:

- **Decompose by conditions or logical steps, never by option.** In multiple-choice questions,
  **do not** create a separate task for each option (`A`, `B`, `C`, `D`, `E`), nor disguise each
  option as an individual task to validate the sentence or topic of that option in isolation.
  Evaluating and comparing the options against the question or a condition is a single goal and
  must stay in a single task.
- **Evaluate options by best relative fit (elimination), without hyper-literalism.** In
  interpretive or multiple-choice questions, the correct option often synthesizes, paraphrases or
  makes a reasonable inference from the text. Do not write descriptions or acceptance criteria that
  require a 100% literal word-for-word presence or that prejudge concepts in the options as absent;
  instruct the task to compare the statements and identify the most coherent one by eliminating the
  most serious distractors. When the comparison involves a calculated value, do not require the
  option to "match exactly" the value: the criterion must require the explicit selection of a single
  option, the one with the closest value or the best fit, recording the difference when there is
  one. Rounding, significant-figure or order-of-magnitude approximations are acceptable; only the
  absence of a selection is unacceptable.
- **Avoid bureaucratic or redundant tasks.** Do not create tasks merely to transcribe literal data
  from the text without analyzing it, nor final tasks to "synthesize previous tasks", "choose the
  final option" or "write the final answer" — consolidating the results and writing the final
  answer belong to a later phase of the flow.
- **Close the gap up to the final quantity or determination asked by the question.** Although each
  task must have an atomic and limited scope, the sequence of tasks must advance until the **last
  task of the plan concludes exactly the final calculation, relation or determination required by
  the question**, consuming the key learnings produced by the previous tasks. For example: if a task
  determines the month in which product I overtakes product II (e.g. August) and the question asks
  what happens in the *following month*, there must be a next task that receives the overtaking
  month from the **Key Learnings** and explicitly determines which month is the following one; if a
  task calculates the quantity already present and the question asks *how much is still missing*,
  the last task must calculate that final difference. Leave to the final synthesis (`C.3`) only the
  presentation of the already determined result and its pairing with the option letter.
- **Keep the criteria concise.** Define only the criteria essential to validate the task
  (typically 2 to 4 criteria per task), without splitting the same requirement into several items.

Together, the tasks must produce enough inputs to support the final answer to the question.

## Examples of scope and explanation

- Valid, in a total-mass task: "Calculate the total mass and explain the calculation; do not
  calculate the mass per spoon". The sentence "the question mentions spoons" is a permitted
  contextual reference. Invalid as a generated criterion: "do not mention spoons" — it forbids words
  without restricting an action.
- Real violation of the previous scope: dividing the total mass by the number of spoons and
  concluding the mass per spoon. Mentioning the next use of the result, without performing that
  calculation, is not a violation.
- Valid: a result accompanied by a verifiable explanation, even if the user wants only the letter
  in the final answer. Invalid: requiring "only the letter, without explanations" from the task, or
  imposing two lines because of "be objective", preventing the justification needed for
  verification.

**Batch limit:** the session holds at most {{max_tasks}} tasks (a safety ceiling, and **not** a
target to reach). Do not exceed this number and do not merge genuinely independent tasks into one
just to fit: keep each one autonomous and single-goal. A batch above the limit is rejected and
returned to you for correction.

Number the tasks starting from `T1`.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"tasks": [{"id": "T1", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}
