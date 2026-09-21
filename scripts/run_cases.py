#!/usr/bin/env python3
"""Send TypeSafe System One request bodies and print answers, token usage and cost.

Standard library only. The input file is a JSON object mapping a name to a native
request body ({"model", "state", "questions"}), like assets/example-requests.json.

    python scripts/run_cases.py --dry-run                 # validate and estimate, no network
    TYPESAFE_API_KEY=... python scripts/run_cases.py      # run the bundled examples
    TYPESAFE_API_KEY=... python scripts/run_cases.py my-requests.json --only support_triage
    python scripts/run_cases.py big-batch.json --env-file .env --concurrency 16

The key comes from TYPESAFE_API_KEY, or from a TYPESAFE_API_KEY= line in --env-file (default .env).
Create one at https://console.typesafe.ai/settings/keys. Requests run concurrently through
jev_client.py, which is also the piece to reuse in application code.

A live run bills the account and sends each request's state to TypeSafe.
Check https://docs.typesafe.ai/api and https://docs.typesafe.ai/models before
relying on the endpoint, limits or price below.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jev_client import JevClient, MissingKey  # noqa: E402

USD_PER_MILLION_INPUT_TOKENS = 0.042  # jev-1.13.0, verified 2026-09-17
TOTAL_TOKEN_LIMIT = 64_000            # state plus all questions
SINGLE_TOKEN_LIMIT = 32_000           # state plus the longest question
CHARS_PER_TOKEN = 4                   # rough estimate for --dry-run only
DEFAULT_FILE = Path(__file__).resolve().parent.parent / "assets" / "example-requests.json"


def validate(name, body):
    problems = []
    for key in ("model", "state", "questions"):
        if key not in body:
            problems.append(f"missing '{key}'")
    for qid, q in body.get("questions", {}).items():
        kind = q.get("type")
        criteria = q.get("criteria")
        if not q.get("instructions"):
            problems.append(f"{qid}: missing instructions")
        if kind == "choice" and not (isinstance(criteria, dict) and 1 <= len(criteria) <= 255):
            problems.append(f"{qid}: choice needs a criteria map of 1-255 options")
        elif kind == "score" and not (isinstance(criteria, list) and 2 <= len(criteria) <= 10):
            problems.append(f"{qid}: score needs a criteria array of 2-10 levels")
        elif kind == "noul" and criteria is not None and not set(criteria) <= {"true", "false"}:
            problems.append(f"{qid}: noul criteria may only contain 'true' and 'false'")
        elif kind not in ("choice", "score", "noul"):
            problems.append(f"{qid}: unknown type {kind!r}")
    return [f"{name}: {p}" for p in problems]


def estimate_tokens(body):
    state = len(json.dumps(body.get("state", ""))) // CHARS_PER_TOKEN
    questions = [len(json.dumps(q)) // CHARS_PER_TOKEN for q in body.get("questions", {}).values()]
    return state + sum(questions), state + max(questions, default=0)


def describe(answer):
    kind = answer.get("type")
    if kind == "noul":
        return f"P(yes)={answer['noul']:.3f}"
    if kind == "choice":
        ranked = sorted(answer["probabilities"].items(), key=lambda item: -item[1])[:3]
        top = ", ".join(f"{option}={p:.2f}" for option, p in ranked)
        return f"{answer['choice']} (confidence {answer['confidence']:.2f}; {top})"
    if kind == "score":
        return f"{answer['score']:.2f} (confidence {answer['confidence']:.2f})"
    return json.dumps(answer)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("file", nargs="?", default=DEFAULT_FILE, type=Path)
    parser.add_argument("--only", action="append", help="run only this named request (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="validate and estimate without calling the API")
    parser.add_argument("--json", action="store_true", help="print raw responses as JSON")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--concurrency", type=int, default=8, help="requests in flight at once")
    parser.add_argument("--env-file", default=".env", help="file to read TYPESAFE_API_KEY from when it is not exported")
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    requests = json.loads(args.file.read_text())
    if args.only:
        missing = set(args.only) - set(requests)
        if missing:
            raise SystemExit(f"not in {args.file.name}: {', '.join(sorted(missing))}")
        requests = {name: requests[name] for name in args.only}

    problems = [p for name, body in requests.items() for p in validate(name, body)]
    if problems:
        raise SystemExit("\n".join(problems))

    if args.dry_run:
        for name, body in requests.items():
            total, single = estimate_tokens(body)
            flag = " OVER LIMIT" if total > TOTAL_TOKEN_LIMIT or single > SINGLE_TOKEN_LIMIT else ""
            print(f"{name}: {len(body['questions'])} questions, ~{total} tokens "
                  f"(~{single} state + longest question), ~${total * USD_PER_MILLION_INPUT_TOKENS / 1e6:.7f}{flag}")
        print("Shapes are valid. Token counts are character-based estimates; a live run reports real usage.")
        return

    try:
        client = JevClient(timeout=args.timeout, retries=args.retries, env_files=(args.env_file,))
    except MissingKey as error:
        raise SystemExit(f"{error}\nUse --dry-run to validate and size requests without a key.")

    names = list(requests)
    started = time.perf_counter()
    responses = client.ask_many([requests[name] for name in names], concurrency=args.concurrency)
    wall = time.perf_counter() - started

    raw, total_tokens, failures = dict(zip(names, responses)), 0, 0
    for name, response in raw.items():
        if "error" in response:
            failures += 1
            if not args.json:
                print(f"\n{name}  FAILED (not judged): {response.get('status', '')} {response['error']}")
            continue
        tokens = response.get("usage", {}).get("input_tokens", 0)
        total_tokens += tokens
        if not args.json:
            print(f"\n{name}  [{response.get('model')}  {response['seconds'] * 1000:.0f} ms  {tokens} input tokens]")
            for qid, answer in response.get("answers", {}).items():
                print(f"  {qid}: {describe(answer)}")
    if args.json:
        json.dump(raw, sys.stdout, indent=2)
        print()
    else:
        print(f"\nTotal: {len(names)} requests in {wall:.2f} s wall at concurrency {args.concurrency}, {failures} failed, "
              f"{total_tokens} input tokens, ~${total_tokens * USD_PER_MILLION_INPUT_TOKENS / 1e6:.7f} "
              f"at ${USD_PER_MILLION_INPUT_TOKENS}/M. Timing includes network from this machine.")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
