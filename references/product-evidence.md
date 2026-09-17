# Jev evidence and integration constraints

Verified against the live docs on 2026-09-17. Everything here is provider documentation, not an independent measurement. Refresh anything version-dependent before you rely on it.

## Contract and limits

| Fact | Primary evidence |
|---|---|
| Jev is TypeSafe AI's first public System One model; it returns typed decisions rather than generated text | [System One](https://docs.typesafe.ai/concepts/system-one) |
| State is a string, JSON object or array of text. No audio, images or video. Prefer an object with descriptive names | [State](https://docs.typesafe.ai/concepts/state) |
| Instructions reference nested state with backticked dot-and-index paths such as `` `support.tickets[0].message` `` | [Building guide](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) |
| Choice selects one option and returns a distribution and confidence. Up to 255 options per Choice (not 255 questions per call); options cost a few tokens each; descriptions may be `null` when names are clear | [Choice](https://docs.typesafe.ai/primitives/choice) |
| Score uses 2–10 described ordered levels and returns their probability-weighted position. Noul returns P(yes) with no separate confidence | [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul) |
| Confidence is computed from how the distribution is spread. Calibration does not guarantee an individual answer | [Confidence](https://docs.typesafe.ai/confidence) |
| Instructions, Choice option descriptions, Score levels and Noul `true`/`false` criteria accept strings or JSON structure (`what`, `not_for`, `examples`, `summary`, `signals`) | [Advanced: structure](https://docs.typesafe.ai/primitives/advanced) |
| **Context window: 64k tokens across state plus all questions; 32k for state plus the longest single question** | [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) |
| `jev-1.13.0`; $0.042 per million input tokens ($42 per billion); output free. Aliases `jev-latest` (SDK default) and `jev-preview` currently resolve to it. `GET /v1/models` lists models for the account | [Models](https://docs.typesafe.ai/models) |
| Documented rate limits: 250,000 tokens/s or 1,200 requests/min, adjusting dynamically and subject to change | [Models](https://docs.typesafe.ai/models) |
| Multiple questions share state and run independently; extra questions cost tokens even where latency barely changes | [Primitives](https://docs.typesafe.ai/primitives), [Fan-out](https://docs.typesafe.ai/patterns/fan-out), [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions) |

## Request and response shape

`POST https://api.typesafe.ai/v1/systemone` with `Authorization: Bearer <API_KEY>` and `Content-Type: application/json`.

```json
{
  "model": "jev-1.13.0",
  "state": "string | object | array",
  "questions": {
    "<question_id>": {
      "type": "noul | choice | score",
      "instructions": "string | object | array",
      "criteria": "noul: optional {true, false} · choice: required {option: description|null} · score: required array of 2–10 levels"
    }
  }
}
```

Composition code reads these answer fields:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "refund_requested": { "type": "noul", "noul": 0.97 },
    "department": {
      "type": "choice",
      "choice": "billing",
      "confidence": 0.94,
      "probabilities": { "billing": 0.96, "delivery": 0.01, "account": 0.01, "other": 0.01, "insufficient_context": 0.01 }
    },
    "resolution_complexity": {
      "type": "score",
      "score": 1.1,
      "confidence": 0.8,
      "legend": { "0": "…", "1": "…", "2": "…" },
      "probabilities": { "0": 0.05, "1": 0.8, "2": 0.15 }
    }
  },
  "usage": { "input_tokens": 412, "output_tokens": 0 }
}
```

The numbers above are invented to show field names. Errors: 401 bad key, 422 validation failure, 429 rate limit, 529 overloaded. Retry 429 and 529 with bounded exponential backoff, and keep a service failure distinct from a negative answer. The response `model` is the resolved version; log it and pin the version you tested, since an alias can move.

## Documented weaknesses of Jev 1.13

From the [jaggedness page](https://docs.typesafe.ai/model-jaggedness/jev-1.13). Design around these rather than prompting against them.

| Weakness | What to do instead |
|---|---|
| **Literal reading:** answers the question written, not the one meant | State exact conditions and boundary cases |
| **Math and numbers:** no calculator | Keep arithmetic in code; pass the computed result as state |
| **Counting** items, characters or occurrences | Count in code; use Jev for per-item semantic judgments |
| **Numeric representations:** hex, RGB triples, binary | Convert to named categories or semantic descriptions first |
| **Date and time comparison:** dates read as text, not ordered quantities | Extract date parts as choices if needed; compare and do arithmetic in code |
| **Indirection:** multi-hop reasoning, double negatives | Write direct, positive instructions and name the relevant state |
| **Irrelevant context:** large unrelated state lowers accuracy | Filter before sending; include only fields the questions need |
| **Adversarial content:** state is not treated as hostile by default | Explicit criteria; test with injected instructions; see [classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) |
| **Contradictory instructions and criteria** | Keep each question's instructions and criteria consistent; one judgment per question |
| **Not trained to generate text; weaker on multi-layer reasoning** | Keep generation and deeper reasoning in a generative model |

## Vendor claims and operations

TypeSafe's [launch article](https://typesafe.ai/blog/introducing-system-one-models-and-jev) advertises 193.6× speed and 444.6× cost improvements on its own workflow evaluations. It calls these high-end gains, acknowledges internal-team bias, and notes that its comparison LLM wrapper requests probabilities, which makes that baseline slower and more expensive than plain decisions. Schema validity is not semantic correctness, so "zero hallucinations" does not mean "cannot make mistakes". The building guide says most queries complete in about 100 ms; no end-to-end latency SLA is documented, so measure with the intended provider, request sizes, region and concurrency, and enforce a request deadline.

No retention or compliance guarantee is assumed here. Check data handling and account terms before sending a private corpus.
