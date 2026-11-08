# A.4 — Key learnings from the question

Record the internal notes about the question below: the points that **must not be lost** when each
task is solved in isolation, without access to this question.

## Question

{{user_question}}

## Instructions

Note down **every piece of data in the question that should catch the attention** of whoever works
on a task without having read the original question, in particular:

- **Names of objects**, terminology, acronyms and their definitions **when supplied**, including
  similar names that identify different objects. Do not guess an acronym's expansion when the
  question does not define it. Preserve symbols and their referents, including case distinctions.
- **Given values**, always with their **units of measurement**, the quantity and the object they
  describe (for example, "The car's speed: 20 m/s"). Keep signs, reference frames and spatial or
  temporal references attached to the values.
- **Tables and lists:** preserve every row and column, their headers, identifiers and associations.
  A code without its meaning is incomplete; do not replace a table with an unassociated list of
  names or numbers.
- **Options** offered, copied **literally**: preserve identifiers and full option texts, with the
  letter or number that identifies each option, without omitting any or detaching its text from
  its identifier. Keep the option mapping as well as any table mapping; one does not replace the
  other. Apply this only when options occur in the question.
- **Formulas**, equations and relations provided.
- **Conditions, constraints and definitions** imposed by the question, including those that hold
  simultaneously.
- Names, dates, codes and any other data that would change the result if they were swapped.
- **Requested determination:** preserve what exactly must be determined, about which object,
  under which simultaneous conditions and in which unit. Record the requested quantity as a
  request, never as an already established result or an acceptance criterion.

Preserve **relations**, not just isolated items: code and meaning; test and parameter; value and
object; distance and spatial reference (which object it is measured from); deadline and event
(what starts the interval); unit and quantity. Keep these associations together in each note,
repeating a supplied name when needed to make the note self-sufficient. Compactness must not remove
an association or condition; a complete table, list or option group may remain in one note.

Each learning is a succinct and dry statement, useful without the question at hand. Copy the data
**as they appear** in the question: do not correct apparent errors, do not convert units, do not
round values, do not classify supplied data as a solution, and do not supplement them with inferred
knowledge. Do not rewrite a supplied relation into a different assertion. If the wording is
ambiguous, preserve the relevant ambiguity and its wording; do not choose an interpretation as if
it were supplied data. Preserve any supplied qualification such as "approximately" or "at least".

**Do not solve the question at this stage.** No conclusion, calculation or answer may appear in the
learnings: record only what the question already states.

It is forbidden to record:

- the solution, the result or any guess about the answer;
- a repetition of the whole question;
- a report of the process or justifications.

When the question brings no data worth recording, return an empty list.

## Completeness review

Before answering, review the question **within this same call**. Check each group of data against
your notes: names and definitions; symbols and referents; values and units; tables and lists;
option identifiers and complete texts; formulas and relations; simultaneous conditions; spatial
references; deadlines and their events; and the requested determination. Check the associations,
not merely whether each number or term appears somewhere. Restore any supplied data or relation
that would otherwise be lost in the next fresh context. Do not solve, infer missing information,
or report this review; return only the notes in the JSON envelope below.

## Output format

Respond **exclusively** with a JSON object, with no text before or after it and no code fence, in
the format:

{"learnings": ["question data 1", "question data 2"]}
