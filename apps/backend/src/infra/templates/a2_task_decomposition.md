# A.2 — Breakdown into single-goal tasks

Plan an ordered sequence of investigations that together determine what the question asks. Each
task has a **single responsibility**. Plan the investigations; do not perform them here.

## Question

{{user_question}}

## Evidence and investigation

Keep these categories distinct in every title, description and acceptance criterion:

- **Literal data:** preserve the relevant values with units, excerpts, formulas, conditions and
  references supplied by the question. These may be copied as given; they are not your findings.
- **Method:** a pertinent law, model or comparison procedure may be planned, such as conservation
  of energy. Choosing a method is not pre-calculating a result. Establish its applicability during
  execution; a formula supplied by the question is still subject to its stated conditions.
- **Hypothesis:** when a method requires an unestablished condition, ask the task to verify that
  condition or justify an explicit assumption and its limits. Never introduce a convenient viewing
  condition, distance reference or physical regime as a supplied fact.
- **Result:** values, qualitative conclusions, classifications, rankings and interpretations still
  to be obtained must remain open. Do not pre-calculate them or embed them in a criterion as the
  required answer. This includes algebraic substitutions and formulas whose applicability depends
  on an unverified hypothesis. For later tasks, name the finding needed from **Key Learnings**;
  do not guess what the preceding task will conclude.

For example, ask to determine which collision has the greater average force and explain the
momentum analysis, rather than require that one named collision have the greater force. Investigate
the source of transferred energy separately from its effect without prescribing the source. For
optical imaging, preserve the requested linear or angular quantity and the reference for each
distance; establish any viewing condition needed by the chosen relation during execution.

## Task scope and criteria

1. **Single goal permits logical dependence.** A task can consume a previous result from Key
   Learnings while having one clear analytical objective. Order the tasks so required findings are
   obtained before use. Each description must preserve the literal data and references relevant to
   its own objective and identify any previous finding it needs.
2. **Fresh context is not absence of memory.** The solver receives its own task, criteria and
   accumulated Key Learnings, not the original question, other task descriptions or their complete
   resolutions. Make each description self-sufficient for its objective, with dependencies supplied
   through memory rather than invented in planning. Copy relevant question content concisely.
3. Give every task its own verifiable criteria, identified as `T1-AC1`, `T1-AC2`, etc. They must be
   **complementary, never mutually exclusive**: one answer must be able to meet all of them at the
   same time. Check criteria in pairs. For example, "answer only the option" conflicts with a
   requirement to explain the internal result. Criteria specify what to determine and how to
   substantiate it, not which as-yet unknown conclusion must be reached.
4. Express scope in an **affirmative and delimiting** way, for example: "the analysis is restricted
   exclusively to the average force comparison and its justification." Restrict actions outside
   this objective, not contextual words. "Do not calculate the mass per spoon" delimits an action;
   "do not mention spoons" unnecessarily forbids a contextual reference. A negative technical
   finding can be a valid result within scope.
5. The task responsible for the **final determination** may perform the last calculation,
   integration or comparison necessary to answer the question. Scope restrictions must allow that
   task's own conclusion, including an explained choice when comparison is substantive analysis.
   C.3 handles presentation and literal pairing of an already supported result with an option
   label; it does not supply missing analysis.
6. Require the result **accompanied by the explanation** of why it is valid, **never the result
   alone**. For calculations, require the formulas used, substitution with units, conventions
   adopted (signs, reference frames, approximations) and justification of the steps. For an
   interpretation, classification or choice, require the supporting evidence and reasoning. Write
   this requirement in the task description and include an acceptance criterion that checks it.
   Internal explanation remains mandatory even if the user requests a short final answer, only a
   letter, or an optional final justification.
7. Interpretive criteria allow supported paraphrases and contextual inference. Do not demand
   literal words from a distractor or impose an unsupported conjunction of aspects. In comparative
   questions, assess best relative fit by elimination, distinguishing serious contradictions from
   reasonable inference rather than requiring a 100% literal match. A supported approximation or
   closest-value choice remains valid when justified by the data, model and precision; do not
   invent a numerical tolerance. Selecting an option alone does not establish correctness.

## Parsimony and efficiency guidelines

Plan the **smallest possible number of tasks** that covers the request, without a preferred count.

- **Decompose by conditions or logical steps, never by option.** Keep comparison of the offered
  statements against a common question or condition in a single investigation.
- **Avoid bureaucratic or redundant tasks.** Do not create tasks merely to transcribe data, print
  a marker or write the final answer. A final integration is warranted when it performs a missing
  inference or comparison; repeating established conclusions for presentation is not an analysis.
- Keep criteria concise and limited to verifiable requirements essential to the objective.

## Final plan review

Before returning the JSON, review the whole plan within this generation. Trace each requested
content obligation to the investigation that will determine it, through the last task needed for
the final quantity or determination. A request for a period in months is not covered by a distance
ratio alone; a request for an amount still missing is not covered by a total already present.
Check that descriptions retain relevant literal data and references, dependencies use actual
future learnings, criteria do not fix uncomputed results, and scopes permit the necessary final
analysis. Revise the plan now if any determination would otherwise be left to C.3.

This review is a planning instruction, not a separate phase or output field. Neither task count
nor JSON validity certifies semantic coverage. C.1 later judges the sufficiency of approved results.

**Batch limit:** the session holds at most {{max_tasks}} tasks, a safety ceiling rather than a
target. Do not exceed this number and do not merge genuinely independent tasks into one just to
fit. Keep each objective clear. A batch above the limit is rejected for correction.

Number the tasks starting from `T1`.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"tasks": [{"id": "T1", "title": "...", "description": "...",
"acceptance_criteria": [{"id": "T1-AC1", "description": "..."}]}]}
