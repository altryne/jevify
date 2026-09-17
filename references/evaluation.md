# Evaluate the decision, not the headline

Start small: a few paired boundary cases to catch a wrong primitive or missing state, then a representative labeled set with separate development and held-out cases. Keep the user's requested scope; an assessment may end with a proposed evaluation rather than running paid inference.

Compare current behavior, a simple deterministic approach, and Jev/hybrid. For LLM comparisons, align evidence, task and quality target. Use structured outputs and batching where they make the baseline fair. Record model/version, reasoning setting, provider, region, date, concurrency, warm/cold calls, repetitions and timeout/retry policy.

Measure:

- Classification: per-label precision/recall, confusion pairs, high-cost false positives, unknown handling and coverage at the chosen abstention rate.
- Retrieval: relevance precision/recall at a fixed candidate pool and output budget; candidate recall separately; downstream answer/task usefulness where feasible.
- Scoring: ranking agreement or correlation with human judgments, per-slice errors, rubric sensitivity. A high model confidence is not a gold label.
- System behavior: p50/p95 wall-clock request and workflow latency, failures, retries, fallback rate, cost and reviewer time.
- Probabilities: Brier score and reliability bins where labels support them; tune thresholds on development data, report held-out results and sample sizes.

Do not tune and report on the same examples without disclosing it. Several questions about the same item are not independent validation. A synthetic four-case success is a smoke test, not production accuracy. Increasing candidate count changes the task/cost; show matched-workload results and expanded-workload results separately.

Input cost = total billed input tokens / 1,000,000 × current price. Count state, instructions/options, all questions, repeated context, retries and other models. Add sensory/retrieval frontend compute and infrastructure where material. Output being free does not make extra questions free. Use returned usage, not a character-count guess, for measured results.

Latency depends on dependency rounds, state size, question count, concurrency, network, limits and queueing. Compare shared-state batching with both serial and batched baselines; do not divide local runtime by a vendor's advertised speedup.

Propose acceptance targets based on consequences: required quality/coverage, p95 budget, cost ceiling and fallback. State what would falsify the recommendation. Cache by evidence + question/rubric + model version; invalidate stale results. Separate uncertain judgments from provider errors. Keep a known fallback and inspect the resulting application behavior, not just individual answers.
