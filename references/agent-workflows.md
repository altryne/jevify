# Use Jev during your own work

The point is to complete the user's task with less bulk reading or repeated judgment. Default to Jev for the bulk semantic work; proceed without a benchmark or a cost-comparison detour. A typical sequence is a small local inspection, a Jev scan, focused source reads, and the answer. Use the task's existing authorization for external inference and data; a key alone does not establish it.

For conversation archives or requirements extraction, use [corpus-review.md](corpus-review.md). A single relevance score cannot preserve speaker authority or recurring goals.

## A long document, one focused question

User: "What does this report say about migration failures and rollback?"

Inspect the file type, size, headings, and a small sample. Extract a PDF or other binary document with an appropriate tool first. If exact search answers the question, use it. If the relevant meaning spans many differently worded sections, let code scan those sections with Jev before loading them into context.

Resolve `JEVIFY_DIR` to the directory containing this skill's `SKILL.md`. Run from the task directory, not the skill directory:

```bash
python3 "$JEVIFY_DIR/scripts/scan.py" report.txt \
  --query "Evidence about migration failures, rollback prerequisites, exceptions, and recovery procedures" \
  --dry-run

python3 "$JEVIFY_DIR/scripts/scan.py" report.txt \
  --query "Evidence about migration failures, rollback prerequisites, exceptions, and recovery procedures" \
  --output migration-scan.json --top 8
```

The first command reads and sizes locally with no key or network. The second sends text and the query to TypeSafe using the task's `TYPESAFE_API_KEY`, or its `.env`. Use `--env-file` for a different project env file. The live command writes a new report and refuses to overwrite an existing file. Use task-local, untracked output paths for private work.

The helper uses one evidence-usefulness Score per unit, with the same four levels across units. Multiple Scores run over shared state in each request. It splits text into overlapping windows, retains character offsets, saves all judgments, and prints only a shortlist. It does not summarize the document, guarantee section boundaries, or decide which evidence is safe to ignore. For structured documents, prepare heading-aware JSONL records with enough context in each `text` field.

Read the selected full passages and adjacent context. Resolve source locations from the report without printing the whole source:

```python
import hashlib
import json
from pathlib import Path

report = json.loads(Path("migration-scan.json").read_text())
raw = Path(report["input"]).read_bytes()
if hashlib.sha256(raw).hexdigest() != report["input_sha256"]:
    raise SystemExit("Input changed; scan again before resolving offsets.")
text = raw.decode("utf-8")
selected_id = "u3"  # choose an ID from the actual shortlist
row = next(row for row in report["results"] if row["id"] == selected_id)
source = row["source"]
if source["field"] == "text":
    text = json.loads(text.splitlines()[source["line"] - 1])["text"]
start = max(0, source["char_start"] - 300)
end = source["char_end"] + 300
print(text[start:end])
```

Offsets are zero-based Unicode character positions with an exclusive end, within the decoded document or a JSONL record's `text` field. JSONL line numbers are one-based. The input hash lets you detect stale locations. Map extracted text back to the original page or section when citations require it.

Default excerpts are capped at 800 characters for eight items. The output also includes bounded low-ranked and uncertain samples for a coverage check. Inspect those originals before relying on the selection; `--audit-size` controls the sample size per group. `--top` and `--excerpt-chars` adjust that context budget. The report shows all judged and unjudged units. A partial failure exits with status 1 while preserving successful judgments. Zero scores are retained as judgments, and even an all-zero shortlist is not proof that the source lacks an answer. Widen the search or read more when the evidence does not settle the question.

## Find every matching item

User: "Find every swear word in this recording."

This is enumeration, not relevance ranking. Use one Noul per sentence, including short reactions, with a concrete inclusion rule. For profanity, include slang and inflections in the criteria without reducing them to a closed wordlist. Save every answer in a file, then have code retain positives above the chosen threshold. Start at 0.5 when no task-specific threshold is known; check candidates and known misses rather than treating that value as validated.

A semantic search tool or `--top 25` returns a shortlist. Increasing top does not establish complete coverage. Use all saved judgments, not the printed shortlist. Track input units, judged units, failed or unjudged units, source truncation and output limits. For an API with bounded threshold results, split overflowing time ranges, rerun affected windows, and deduplicate by stable source bounds. Retrieve only the selected text and necessary neighbors into reasoning context. Complete processing and perfect recall are different claims.

If the request names an exact string, use literal search over a file-backed export. For a semantic class, use Jev rather than paging the whole source into context and inventing a regex wordlist. A missing known hit can come from input filtering, truncation, ranking or the question itself; inspect which stage lost it before rewriting the question.

Muse's September 21 Targum review reported 16 transcript reads plus grep in 27 seconds, compared with a Jev scan of 1,710 sentences in 2.5 seconds for $0.013. Jev found two slang terms the regex missed, while the top-ranked response still omitted other hits. These are attributed session observations, not a controlled benchmark or a guarantee. The reusable lesson is to separate enumeration from shortlisting.

## Large tool outputs and records

User: "These deployment runs keep failing. Find the common cause."

Prefer a tool's export or pagination support. For a command-line source, redirect the full result to a task file and print only counts, schema, and a small sample. If output is already in context, do not claim a scan will save that context retroactively.

Convert relevant records to JSONL using code. Each line needs a `text` string. Optional string fields `id`, `role`, and `conversation_id` are preserved as metadata and sent with the text. Other fields stay local. Keep authoritative source locations in a local manifest. Include the semantic context needed for interpretation inside `text`, such as a run's stage, error summary, and neighboring events. Remove secrets before scanning.

```json
{"id":"run-a","text":"Build completed. Deploy failed after the health check rejected the new server. The previous version remained active."}
{"id":"run-b","text":"The installer could not resolve a package. No deploy was attempted."}
```

```bash
python3 "$JEVIFY_DIR/scripts/scan.py" runs.jsonl \
  --query "Evidence explaining why deployments fail after a successful build" \
  --output deployment-scan.json --top 6
```

The helper uses line numbers and within-record offsets as source locations, even if record IDs are duplicated. It ranks evidence for inspection. Follow the actual run records and verify the cause. For a complete category breakdown, build per-record Choice or Noul questions and aggregate every result in code instead of counting a shortlist.

## More than a relevance scan

The scan helper deliberately does one job. Use the existing TypeSafe tool, the official SDK for the project's language, or the bundled standard-library client for other judgments. Python does not require npm; this fallback also avoids pip dependencies. Run a Python helper for your own analysis without making it a dependency of the product you are editing.

A single request can choose a handler and judge independent conditions over the same state:

```python
from jev_client import JevClient  # import from the skill's scripts directory or a task-local copy

client = JevClient()
result = client.ask(
    state={"request": "The shipment arrived broken. Please send a replacement."},
    questions={
        "handler": {
            "type": "choice",
            "instructions": "Which team should take primary responsibility for `request`?",
            "criteria": {
                "returns": "Damaged products, replacements, and exchanges",
                "billing": "Charges and payment processing",
                "other": "No supplied team fits",
                "unknown": "Insufficient evidence to choose",
            },
        },
        "replacement_requested": {
            "type": "noul",
            "instructions": "Does `request` ask for a replacement item?",
        },
    },
)
if "error" in result:
    raise RuntimeError("Request was not judged; use the task's fallback.")
answers = result["answers"]
# Code consumes answers["handler"]["choice"] and answers["replacement_requested"]["noul"].
```

This is an example request, not a measured result or permission to send it. Each question is complete without seeing the other answer. Add independently needed questions to the request; don't make a round trip per question. Refer to [question-design.md](question-design.md) for multi-select, criteria, uncertainty, and speculative questions.

## Runtime and throughput

All bundled scripts use Python 3.10+ and the standard library. Outbound HTTPS access and a TypeSafe key are needed for live calls. An existing SDK or tool is equally valid.

Use `scan.py --help` for current batch, chunk, overlap, concurrency, and output settings. The scanner uses serialized bytes as a sizing heuristic rather than the provider's tokenizer. Refresh model limits, compare quality across unit sizes, and use actual returned usage for measurements. [running-jev.md](running-jev.md) covers throughput, failures, and caching.

The report records returned input tokens and resolved model versions. Retry usage may be missing from final responses, so these counts are not a full billing reconciliation. A different `--model` has no price estimate until its price is verified.

## "Jevify this" while building a product

Inspect the actual behavior and repeated decisions first. A useful proposal names the user-visible change: checking a draft as it is written, ranking more candidates without a slow blocking step, or routing simple cases before invoking a reasoning model. Show exact state and questions, how code consumes the answers, and what the user experiences.

Explain how the change improves the experience, use the known economics for a quick estimate when useful, and verify that the resulting feature works. The existing [worked question pack](worked-question-pack.md) supports detailed proposals. Use the [evaluation guide](evaluation.md) when a benchmark or formal quality evaluation is requested. Broader community research is useful when it can change the design; it is not required before every call.
