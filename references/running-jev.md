# Running Jev

Use this reference for execution, credentials, batching, and failures. For large-input commands and source retrieval, read [agent-workflows.md](agent-workflows.md). For a specific recurring failure, consult [field-notes.md](field-notes.md); those historical examples are not prerequisites for a scan.

## Choose the runtime

Use the existing TypeSafe tool or the project's matching official SDK when available. The [official Python SDK](https://docs.typesafe.ai/sdk/python) works without npm. The bundled [jev_client.py](../scripts/jev_client.py) additionally avoids third-party Python packages, which suits assistants that can execute Python but cannot install dependencies. Import or copy it for a standalone task; keep product integrations in their existing stack.

The bundled command-line helpers resolve imports relative to themselves. Run them from the task directory and use absolute script paths resolved from the installed skill location. Keep outputs and project credentials with the task. Inspect `--help` for current flags.

## Credentials

Check for `TYPESAFE_API_KEY` in the environment or the project's specified env files by presence only. Keys are created at [the TypeSafe console](https://console.typesafe.ai/settings/keys). The helpers read the environment first and then `.env`, or a file supplied with `--env-file`.

If missing, tell the user the variable name and console location once. They can export it in the process environment or set it in a git-ignored project env file. Continue local parsing, question design, or dry-run sizing while waiting. Stop credential lookup at the task's environment and specified project files.

Keep credentials out of prompts, logs, code, and run records. Web applications keep keys server-side; deployed services use the platform's secret store. The official SDK supports its documented environment variables; the bundled client accepts its own explicit constructor arguments and does not mirror every SDK setting.

## Batch for the actual workload

Ask independent questions over shared evidence together. State is billed once per request; instructions and criteria add tokens for every question. Additional questions can make better use of a request without another network round trip. Dependent stages still need new evidence or options before their next request.

Use a bounded pool for requests that remain. The bundled client reuses connections within worker threads and paces starts by request count. It does not enforce token throughput or coordinate with other clients using the account.

The [current model limits](https://docs.typesafe.ai/models), verified September 21, 2026, are 1,200 requests per minute and 250,000 tokens per second. At 20 requests per second, 15,000-token requests need 300,000 tokens per second. Plan for both limits. Compare quality across batch sizes as well as speed; even candidates sharing a query can influence one another through shared state.

Fit both context budgets: 64k tokens for state plus all questions, and 32k for state plus the longest question. Retrieve focused evidence or split units when needed. The scanner uses a conservative serialized-byte sizing heuristic; the general request runner uses a rough character estimate. Neither is the provider's tokenizer. Measure actual usage, leave headroom, and handle validation errors explicitly.

Check the current model and account limits before relying on these values. Treat rates and batch sizes as workload settings, not permanent recommendations.

## Failures, retries, and caching

Treat failed requests, malformed answers, and missing answers as unjudged. Report partial coverage and use the task's fallback. Successful judgments should remain available when another batch fails. The scanner saves successful and unjudged source locations and exits nonzero on partial failure.

The official SDKs implement retries. For direct HTTP clients, follow current provider guidance for rate limits and overloads. The bundled client retries those responses with bounded backoff; its timeout applies per attempt, not to the entire workflow. Its compact implementation is a fallback, not full SDK parity. Use an end-to-end deadline where the user experience requires one.

For repeat work, the optional client cache hashes the request body. Pin the model version when caching or evaluating; an alias can change without changing the cache key. Changing source evidence or question meanings requires fresh judgments. Changing weights or display filters can reuse the same answers. Retain exact source locations and an input version so stale results cannot be applied to changed data.

## Report what ran

Record returned input tokens, resolved model versions, actual wall time, failures, and coverage. Request estimates and a dry run are preparation, not inference results. Returned usage from final successful responses may omit billed retry attempts; distinguish it from account-level billing.

For an explicitly requested comparison or a performance investigation, use [evaluation.md](evaluation.md). Ordinary execution proceeds on the default that Jev is the faster, cheaper choice for bulk semantic judgments, with source and behavior checks appropriate to the task. The [field notes](field-notes.md) offer hypotheses for debugging; their historical timings and small-case results are not guarantees for a new workload.
