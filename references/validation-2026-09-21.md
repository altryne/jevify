# Validation on September 21, 2026

These checks exercise the bundled helpers and a small synthetic message pack. They do not establish archive-wide recall, measured savings over a reasoning model, or automatic skill activation.

## Local checks

Run from the repository root:

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/run_cases.py --dry-run
python3 scripts/run_cases.py assets/message-signals.json --dry-run
git diff --check
```

Eight tests passed. They cover exact Unicode offsets and window coverage, duplicate source IDs, preserved roles, request sizing and targets, partial failures, zero scores, bounded output, audit samples, and overwrite protection. A malformed HTTP response and a rejected request did not discard a later successful response. Provider error bodies stayed out of returned diagnostics.

## Live synthetic checks

The tests used the bundled standard-library client and `jev-1.13.0`. Credentials came from a specified local env file and were not copied into the repository. Every input was synthetic.

- The initial message pack returned 16 judgments in 0.32 seconds using 1,772 input tokens. It exposed an ambiguous friction question: "correct behavior" caused praise to score 0.84 as friction. A complaint about manual work scored only 0.32 as a goal.
- After the question rewrite, the same 16 judgments took 0.30 seconds and 2,344 input tokens. The praise example scored 0.03 for friction and 0.98 for positive feedback. The complaint scored 0.81 for a goal. This is a tuned rerun, not held-out accuracy.
- Four fresh messages used the revised questions without another edit. The 16 judgments took 0.30 seconds and 2,348 input tokens. A bulk-action request scored 0.97 for a goal and 0.98 for friction. A praise message scored 0.98 for positive feedback and 0.05 for friction. A neutral fact scored 0.07 for a goal and 0.08 for friction. These few author-written examples are still smoke tests.
- A scanner run judged all 24 synthetic deployment records in three requests with no failures. It took 0.40 seconds and 5,363 input tokens. The report retained every source location and role, while stdout contained two top items and four audit samples. The top two repeated the same failure type, which demonstrates why a small shortlist cannot establish coverage of every cause.

Total returned input usage was 11,827 tokens across six requests and 72 judgments. At the verified price of $0.042 per million input tokens, that is approximately $0.000497 before any usage omitted by responses. Timings include network time from one machine. This is not an account billing reconciliation or a latency benchmark.

The synthetic pack can be rerun with `scripts/run_cases.py assets/message-signals.json` when external inference is authorized. The original and fresh-message result summaries remain task-local. No private archive, credentials, or local source paths are published here.
