# Designing questions that Jev can answer usefully

Use current [primitives](https://docs.typesafe.ai/primitives), [Choice](https://docs.typesafe.ai/primitives/choice), [Noul](https://docs.typesafe.ai/primitives/noul), [Score](https://docs.typesafe.ai/primitives/score), and [structured question guidance](https://docs.typesafe.ai/primitives/advanced). The request examples here are designs to adapt; none has recorded model output.

## Work backward from the action

What will software do: choose one handler, retain all useful passages, flag a defect, rank utility, or select a source value? That determines the primitive. “Make this workflow smarter” is not a question.

State contains evidence: named records, current facts, candidate text, relationships and context. Instructions define the judgment. Criteria define the answer boundary. Point instructions at state with backticked paths such as `` `ticket.message` `` or `` `candidates.p2.text` ``; the docs use that convention so there is no doubt which value a question is about.

Retrieve focused evidence first. Add context when errors expose a gap, not every document available: unrelated state lowers accuracy, and the window is finite (64k tokens for state plus all questions, 32k for state plus the longest question in Jev 1.13; check current limits). When the evidence will not fit, filter or retrieve harder, trim records to the fields the questions use, or split candidates into groups that each carry the shared query. Splitting repeats the shared state, so count that in cost.

Build a compact contract: target, evidence, judgment, answer meaning, exclusions, missing-data behavior. Keep a short string when clear. Use an object when named fields separate tangled definitions or examples. Long structured prompts are not mandatory.

## Choice: which one?

Use mutually exclusive operational outcomes. When topics overlap, specify the selection basis: primary requested remedy, best next handler, or best supported candidate. `other` means no option matches; `insufficient_context` means the evidence cannot settle it.

Bad: “Classify this,” with billing, support and urgent as options. Billing is a topic, support a department, urgent an independent property.

Better: ask for the primary requested remedy, define comparable departments, and ask urgency separately. Contrast neighboring options with consistent `what`, `not_for`, and `examples` fields where needed. Check coverage: Jev cannot choose a missing candidate.

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

## Improve from errors

Use labeled cases covering clear yes/no, neighboring classes, several valid items, absent evidence, contradictory context, negation, misleading instructions in data, and unfamiliar wording. Include paired cases differing only in the crucial detail.

Inspect whether required evidence/candidates existed before changing prompts. Identify wrong targeting, overlapping options, vague levels, missed relationships, composition errors or model error. Try the smallest relevant change: scope, contrastive definitions, an example, a different primitive or another retrieval stage. Compare on held-out cases with the same version/settings. Test strings against structured criteria where useful. Higher confidence alone is not evidence of improvement.

There is no universally best question format or threshold. Recommend a reasoned starting design, then use quality, coverage, cost and resulting application behavior to choose revisions.

[question-cases.json](../assets/question-cases.json) supplies nine human-authored boundary cases for these examples. They are evaluation seeds written by hand.
