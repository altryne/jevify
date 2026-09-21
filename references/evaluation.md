# Evaluate the decision, not the headline

Use this reference for requested benchmarks, formal evaluations, or performance investigations. It is not a prerequisite for ordinary Jev use. Default to Jev for bulk semantic judgments and complete the task; routine source and behavior checks still apply.

Start small: a few paired boundary cases to catch a wrong primitive or missing state, then a representative labeled set with separate development and held-out cases. Keep the user's requested scope; an assessment may end with a proposed evaluation rather than running paid inference.

## Include the agent's own spend

The reasoning agent's tokens and time are part of the workload. Compare completing the same user task by direct reading with using Jev to select evidence or perform repeated judgments first. Record:

- Reasoning-model input and output tokens, cached input where available, and actual model or reasoning setting.
- Jev input tokens across all questions and requests, plus retry and fallback usage where available.
- The amount of source material loaded into the agent's context, and the selected evidence returned after preprocessing.
- End-to-end time and result quality, including the agent's source verification and the user's review work.

With known token prices, compare total reasoning-model cost against Jev plus the remaining reasoning-model and other tool costs. If reasoning-token usage, cache accounting, or effective subscription pricing is unavailable, report the observable reduction in loaded material or work as a proxy and state the limitation. A character reduction is not an exact token saving. Lower token use can conserve a user's allowance without establishing a dollar saving on a subscription.

Delegating a large first pass can reduce expensive reading and repeated reasoning. Loading the whole input first, adding Jev, and then repeating the full reasoning task adds work instead. Identify what the Jev pass actually replaces before attributing a benefit. Already-cached or small inputs may favor direct reading. Keep a fair baseline with the same task and quality requirement.

## Evaluate the result

Compare current behavior, a simple deterministic approach, and Jev/hybrid. For LLM comparisons, align evidence, task and quality target. Use structured outputs and batching where they make the baseline fair. Record model/version, reasoning setting, provider, region, date, concurrency, warm/cold calls, repetitions and timeout/retry policy.

Measure:

- Classification: per-label precision/recall, confusion pairs, high-cost false positives, unknown handling and coverage at the chosen abstention rate.
- Retrieval: relevance precision/recall at a fixed candidate pool and output budget; candidate recall separately; downstream answer/task usefulness where feasible.
- Scoring: ranking agreement or correlation with human judgments, per-slice errors, rubric sensitivity. A high model confidence is not a gold label.
- System behavior: p50/p95 wall-clock request and workflow latency, failures, retries, fallback rate, cost and reviewer time.
- The user's clock: minutes from the person's first action to a finished result, against doing the same task by hand. Fast, cheap judgments can still lose this comparison when they generate more review work than they remove; measure it early, with the person, before scaling the output.
- Probabilities: Brier score and reliability bins where labels support them; tune thresholds on development data, report held-out results and sample sizes.

**Say who made the labels.** Labels you wrote yourself are your opinion, and agreement with them shows that Jev moved toward your view, not that it is accurate. A user in one session put it directly: "you just compare to what YOU think is better?" Report every number with who labeled, how many items, how they were chosen, and whether they were also used for tuning. Hand-picked clear cases separate easily and say little about the borderline ones that decide product quality. Repeats of the same items measure run-to-run noise only. "I agreed with all 12 proposals" is grading your own pipeline.

For subjective editorial or product judgments, the decision owner is a useful source of labels. Objective tasks can instead use verifiable facts, executable checks, or qualified annotators. Two ways to collect preference labels: their accept and reject actions on what the system proposes, turned into per-question precision by reason; and blind labeling, where they mark a random sample that mixes clear and borderline items with Jev's answers hidden and unsorted, since seeing the model's answer first anchors the label. A small blind sample can expose disagreements hidden by self-labeling. Choose sample size and acceptance criteria based on task variability and error costs; disclose who supplied the labels and what they establish.

Do not tune and report on the same examples without disclosing it. Several questions about the same item are not independent validation. A synthetic four-case success is a smoke test, not production accuracy. Increasing candidate count changes the task/cost; show matched-workload results and expanded-workload results separately.

Input cost = total billed input tokens / 1,000,000 × current price. Count state, instructions/options, all questions, repeated context, retries and other models. Add sensory/retrieval frontend compute and infrastructure where material. Output being free does not make extra questions free. Use returned usage, not a character-count guess, for measured results.

Latency depends on dependency rounds, state size, question count, concurrency, network, limits and queueing. Compare shared-state batching with both serial and batched baselines; do not divide local runtime by a vendor's advertised speedup.

Propose acceptance targets based on consequences: required quality/coverage, p95 budget, cost ceiling and fallback. State what would falsify the recommendation. Cache by evidence + question/rubric + model version; invalidate stale results. Separate uncertain judgments from provider errors. Keep a known fallback and inspect the resulting application behavior, not just individual answers.

For the bundled helper checks and small live synthetic runs, see [the September 21 validation note](validation-2026-09-21.md). This records execution evidence, not a completed agent comparison.
