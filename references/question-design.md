# Designing questions that Jev can answer usefully

Use current [primitives](https://docs.typesafe.ai/primitives), [Choice](https://docs.typesafe.ai/primitives/choice), [Noul](https://docs.typesafe.ai/primitives/noul), [Score](https://docs.typesafe.ai/primitives/score), and [structured question guidance](https://docs.typesafe.ai/primitives/advanced). The request examples here are designs to adapt; none has recorded model output.

## Work backward from the action

What will software do: choose one handler, retain all useful passages, flag a defect, rank utility, or select a source value? That determines the primitive. “Make this workflow smarter” is not a question.

State contains evidence: named records, current facts, candidate text, relationships and context. Instructions define the judgment. Criteria define the answer boundary. Point instructions at state with backticked paths such as `` `ticket.message` `` or `` `candidates.p2.text` ``; the docs use that convention so there is no doubt which value a question is about.

Retrieve focused evidence first. Add context when errors expose a gap, not every document available: unrelated state lowers accuracy, and the window is finite (64k tokens for state plus all questions, 32k for state plus the longest question in Jev 1.13; check current limits). When the evidence will not fit, filter or retrieve harder, trim records to the fields the questions use, or split candidates into groups that each carry the shared query. Splitting repeats the shared state, so count that in cost.

Build a compact contract: target, evidence, judgment, answer meaning, exclusions, missing-data behavior.

## Tell Jev what it is looking at

Jev knows nothing about the user's world. A question like "Is this sentence the host operating the show?" arrives cold: nothing says the text is a live broadcast, that the host also runs the screen share, or that the decision is what to trim for a podcast. A human given the same task would need that briefing, and so does Jev.

Put a short domain context block in state and point the questions at it: what this material is, who is involved, what the decision is for, and any local convention that changes the right answer. Five plain sentences is plenty. Keep it in its own named field, separate from the item being judged.

Then test it per question, because context is not free accuracy. In one session a context block widened the gap between labeled yes and no cases for editorial questions (is this production chatter, would a listener miss this) and narrowed it for a purely linguistic one: once told that speakers on this show restart sentences all the time, Jev treated false starts as normal. Send each question only the context notes that bear on it.

When questions are built from a template, keep the person's wording and the machine-inserted pointer in separate fields of structured instructions (`question` for the words, `inspect` or `target` for the backticked path) rather than gluing a path into the middle of a sentence. It keeps the prompt readable to both the model and the person debugging it.

## Instructions and criteria can be JSON, not only state

Most people structure the state and then write `instructions: "classify this as a foo or bar"` with one-line criteria. Instructions, Choice option descriptions, Score levels and Noul `true`/`false` criteria all accept objects and arrays ([Advanced: structure](https://docs.typesafe.ai/primitives/advanced)), and a TypeSafe engineer has called this very important for prompt optimization and the least obvious of the three places JSON is accepted (see [community-discoveries.md](community-discoveries.md), finding 9). It is specific to Jev: there is no chat template to fight, so labeled fields are read as labeled fields.

Structured instructions separate the kinds of guidance a question carries, and can carry per-question context that does not belong in shared state:

```json
{
  "type": "choice",
  "instructions": {
    "question": "What is the text inside [[double brackets]] in `target.sentence` doing in that sentence?",
    "focus": "Judge only the bracketed occurrence, not other uses of the same word",
    "context": "Spoken podcast transcript; speakers restart and trail off",
    "previous_judgments": [
      { "sentence": "It was, [[like]], amazing.", "answer": "discourse_filler" },
      { "sentence": "Tasks [[like]] stacking blocks.", "answer": "comparison_or_example" }
    ]
  },
  "criteria": {
    "discourse_filler": {
      "what": "A verbal tic; the sentence reads the same without it",
      "not_for": "like meaning 'similar to'; like as a verb",
      "examples": ["so, you know, we shipped it", "I mean, at the start of a turn"]
    },
    "comparison_or_example": {
      "what": "Introduces a comparison or an example",
      "examples": ["a model like Astra", "feels like AGI"]
    },
    "insufficient_context": "The sentence does not settle it"
  }
}
```

Field names are yours to choose; the docs use `question`, `focus`, `compare`, `inspect`, `field`, `what`, `not_for`, `examples`, `summary` and `signals`. Use the same field names across all options or levels so the model can compare like with like. A schema, taxonomy node or database row that is already JSON can go in as it is.

When to reach for it: neighboring options blur, a question needs worked examples or prior decisions, or the instruction has several parts (what to judge, what to ignore, what the source is). A short string is still right for a simple question. Structured fields cost tokens on every question that carries them, so when a rubric is shared by many questions in a request, weigh its size (see [running-jev.md](running-jev.md)). One small community test saw flat and structured criteria tie, so treat structure as a strong default for ambiguous judgments and confirm it on labeled cases rather than assuming either way.

## Choice: which one?

Use mutually exclusive operational outcomes. When topics overlap, specify the selection basis: primary requested remedy, best next handler, or best supported candidate. `other` means no option matches; `insufficient_context` means the evidence cannot settle it.

Bad: “Classify this,” with billing, support and urgent as options. Billing is a topic, support a department, urgent an independent property.

Better: ask for the primary requested remedy, define comparable departments, and ask urgency separately. Contrast neighboring options with consistent `what`, `not_for`, and `examples` fields where needed. Check coverage: Jev cannot choose a missing candidate. Options must also be genuinely different outcomes: near-duplicate options (machine-generated candidates that differ by a word) split the probability between them so that none wins clearly. Merge them, or judge each with its own Noul.

A Choice distribution allocates probability among competing winners and sums to 1. That makes it a good cheap ranker and a poor inclusion test. The official [semantic find](https://docs.typesafe.ai/cookbooks/semantic_find) and [skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion) cookbooks rank 218 line IDs and 182 skills with a single Choice, then cover its blind spots: some option always ranks first even when nothing matches, so they add a Noul asking whether any answer exists, and skill suggestion re-checks the top three with per-item Nouls over fuller text. Use that shape when you want a shortlist or one best item from a long list. When several items can all qualify and each must be kept or dropped, as in memory or passage selection, ask one Noul per candidate or comparable per-item Scores; community tests found Choice ranking dropped relevant items there. Above the documented option limit, retrieve candidates or use [hierarchical selection](https://docs.typesafe.ai/cookbooks/hierarchical_classification), and measure candidate recall.

## Noul: is the condition true?

Use positive, explicit conditions: near 1 means yes; near 0 means no. Near 0.5 means uncertainty, not medium intensity. There is no separate confidence field. A clear no can be useful and confident.

Bad: “Is this not an unimportant message?”

Better: “Does `ticket.message` explicitly request a response before the supplied deadline?” Define yes/no in criteria and compute deadline ordering in code, because Jev reads dates as text rather than ordered quantities. The same goes for arithmetic and counting: pass `minutes_until_deadline: 42`, not two timestamps. If the desired judgment is importance, use a defined utility Score instead.

For multi-label tasks, one complete question per label; for retrieval, one per candidate. Name the target inside instructions: keys such as `candidate_7` are not instructions. Preserve both sides of relationships being judged.

When absence and uncertainty need different actions, use a Choice including unknown or add a sufficiency check. “Source supports the claim” is not “the claim is true in the world.” Evidence absent from the source does not establish falsity.

## Score: how much of one property?

Define one ordered dimension using concrete situations. Current docs specify 2–10 levels. Each description must stand alone; levels are judged individually. Array positions start at zero. A fractional score is a position over those levels, not a physical measurement or a percent-correct estimate.

Bad: poor / okay / good / excellent without definitions, or levels mixing relevance, politeness and speed.

Better for evidence usefulness:

- No information that helps answer the query.
- Background that explains the query but does not answer it.
- Answers part of the query with concrete evidence.
- Directly answers the query with concrete evidence.

Use separate dimensions when code will weight them differently. Keep the rubric comparable across candidates. Normalize by `levels.length - 1` only when that position scale fits the application. Never interpolate an invoice amount from Score; extract/select the literal value and calculate in code. Route unknown separately, not as the top of an ordered severity scale.

## Batch and compose

Independent questions over shared state belong in one request. Extra questions still cost tokens and count toward the context window and rate limits. For speculative branches, state the premise: “If the billing workflow handles this request, which supplied invoice does the customer refer to?” Code uses it only on that branch.

Bad: `q2: Why did q1 choose billing?` in the same request. Questions cannot see each other's answers, and Jev cannot write the explanation.

Better: independently classify intent and select an invoice over shared evidence. Code routes. If invoice details must be fetched after selection, fetch and make a second request. Shared-state batching is not an invitation to concatenate unrelated tasks until relevance collapses.

Weighted sums allow preferences to compensate; hard requirements cannot be averaged away. Correlated probabilities cannot simply be multiplied into a calibrated joint answer. Permission checks remain outside inference.

## Ready-to-adapt request examples

[example-requests.json](../assets/example-requests.json) contains complete proposed native HTTP bodies for `POST https://api.typesafe.ai/v1/systemone`. It pins the model verified when written; refresh before running. All state is synthetic and no outputs are included. [worked-question-pack.md](worked-question-pack.md) turns the first example into a full deliverable with composition code, and [run_cases.py](../scripts/run_cases.py) can send these bodies when the user wants a live check.

1. **Support triage:** Choice department, Noul refund request, Score resolution complexity. Code selects a handler, then a specialist/review path. A refund request is not payment authorization; a low Noul is not a service failure.
2. **Evidence filtering:** one Noul per candidate. Retain multiple useful passages with a validated threshold and budget. Do not force exactly one item or fill the budget with irrelevant results. Add comparable per-item Scores if utility ranking matters.
3. **Source-value extraction:** Choice over span IDs plus not-stated/ambiguous. Code resolves the exact source string. Candidate generation and coverage remain a separate recall problem.

## Check that the question is doing work

Look at the distribution of answers before trusting a pack. If nearly every item gets the same answer (874 of 886 in one run), the question is probably answering itself. Two ways that happens: an option's description names the very tokens being judged ("a filled pause: uh, um, er" applied to the word "uh"), so Jev matches the word instead of judging the use; or the question is trivially true for the whole category ("does the sentence state the same facts without this uh?"). A question written for one kind of target rarely transfers to another. Go back to what the person cares about for this target and ask that, and move whatever code can measure (pause length, position, counts) into code.

## Improve from errors

Use labeled cases covering clear yes/no, neighboring classes, several valid items, absent evidence, contradictory context, negation, misleading instructions in data, and unfamiliar wording. Include paired cases differing only in the crucial detail.

Inspect whether required evidence/candidates existed before changing prompts. Identify wrong targeting, overlapping options, vague levels, missed relationships, composition errors or model error. Try the smallest relevant change: scope, contrastive definitions, an example, a different primitive or another retrieval stage. Compare on held-out cases with the same version/settings. Test strings against structured criteria where useful. Higher confidence alone is not evidence of improvement.

There is no universally best question format or threshold. Recommend a reasoned starting design, then use quality, coverage, cost and resulting application behavior to choose revisions.

[question-cases.json](../assets/question-cases.json) supplies nine human-authored boundary cases for these examples. They are evaluation seeds written by hand.
