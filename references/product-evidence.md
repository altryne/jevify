# Jev evidence and integration constraints

Verified 2026-09-17. Refresh these sources when using the skill. These are provider documentation claims, not an independently measured benchmark.

| Fact | Primary evidence |
|---|---|
| Product is Jev, TypeSafe AI's first public System One model; typed decisions rather than generated text | [System One](https://docs.typesafe.ai/concepts/system-one) |
| Text/JSON state only; no audio, images, or video | [State](https://docs.typesafe.ai/concepts/state) |
| Choice selects an option with a distribution and confidence; up to 255 options per Choice, not 255 questions per call | [Choice](https://docs.typesafe.ai/primitives/choice) |
| Score uses 2–10 described ordered levels and returns their probability-weighted position; Noul returns P(yes), without a separate confidence | [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul) |
| Confidence is derived from the returned distribution; calibration does not guarantee an individual answer | [Confidence](https://docs.typesafe.ai/confidence), [System One](https://docs.typesafe.ai/concepts/system-one) |
| `jev-1.13.0`; $0.042 per million input tokens; output free. Current documented limits: 250,000 tokens/s and 1,200 requests/min, explicitly subject to change | [Models](https://docs.typesafe.ai/models) |
| 64k tokens total state plus questions; 32k state plus longest question. Literal reading, numeric precision, indirection, irrelevant context, and adversarial state are documented weaknesses | [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) |
| Native API: POST `https://api.typesafe.ai/v1/systemone` with `model`, `state`, `questions`; response includes answers and token usage. 429/529 need bounded retries/backoff | [API](https://docs.typesafe.ai/api) |
| Multiple questions share state and run independently; extra questions cost tokens even where latency changes little | [Primitives](https://docs.typesafe.ai/primitives), [Fan-out](https://docs.typesafe.ai/patterns/fan-out) |

TypeSafe's [launch article](https://typesafe.ai/blog/introducing-system-one-models-and-jev) advertises 193.6× speed and 444.6× cost improvements on its workflow evaluations. It calls these high-end gains, acknowledges internal-team bias, and notes that the comparison LLM wrapper requests probabilities and is slower/more expensive than decisions without them. Its schema-validity claim is not a semantic-correctness guarantee. Do not repeat “zero hallucinations” as “cannot make mistakes.”

No universal end-to-end latency SLA was established in this research. Measure the intended provider, request sizes, region and concurrency. SDK retries and aliases can alter operational behavior: log the returned version, pin the tested version, enforce a request deadline, and keep errors/uncertainty distinct from a negative answer.

Useful documented patterns: [line ID selection](https://docs.typesafe.ai/cookbooks/semantic_find), [source-supported citation checks](https://docs.typesafe.ai/cookbooks/citation_check), and [candidate value selection](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook). They justify experiments, not claims of tested performance in another domain. Verify data handling and account access before sending a private corpus; no retention or compliance guarantee is assumed here.
