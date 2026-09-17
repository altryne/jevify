#!/usr/bin/env python3
"""Send TypeSafe System One request bodies and print answers, token usage and cost.

Standard library only. The input file is a JSON object mapping a name to a native
request body ({"model", "state", "questions"}), like assets/example-requests.json.

    python scripts/run_cases.py --dry-run                 # validate and estimate, no network
    TYPESAFE_API_KEY=... python scripts/run_cases.py      # run the bundled examples
    TYPESAFE_API_KEY=... python scripts/run_cases.py my-requests.json --only support_triage

A live run bills the account and sends each request's state to TypeSafe.
Check https://docs.typesafe.ai/api and https://docs.typesafe.ai/models before
relying on the endpoint, limits or price below.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
USD_PER_MILLION_INPUT_TOKENS = 0.042  # jev-1.13.0, verified 2026-09-17
TOTAL_TOKEN_LIMIT = 64_000            # state plus all questions
SINGLE_TOKEN_LIMIT = 32_000           # state plus the longest question
CHARS_PER_TOKEN = 4                   # rough estimate for --dry-run only
RETRY_STATUSES = {429, 529}
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


def post(body, api_key, timeout, retries):
    data = json.dumps(body).encode()
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            ENDPOINT,
            data=data,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response), time.perf_counter() - started
        except urllib.error.HTTPError as error:
            if error.code in RETRY_STATUSES and attempt < retries:
                time.sleep(2**attempt)
                continue
            raise SystemExit(f"HTTP {error.code}: {error.read().decode(errors='replace')[:500]}")
    raise SystemExit("retries exhausted")


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

    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise SystemExit("Set TYPESAFE_API_KEY, or use --dry-run.")

    raw, total_tokens = {}, 0
    for name, body in requests.items():
        response, seconds = post(body, api_key, args.timeout, args.retries)
        raw[name] = response
        tokens = response.get("usage", {}).get("input_tokens", 0)
        total_tokens += tokens
        if not args.json:
            print(f"\n{name}  [{response.get('model')}  {seconds * 1000:.0f} ms  {tokens} input tokens]")
            for qid, answer in response.get("answers", {}).items():
                print(f"  {qid}: {describe(answer)}")
    if args.json:
        json.dump(raw, sys.stdout, indent=2)
        print()
    else:
        print(f"\nTotal: {total_tokens} input tokens, ~${total_tokens * USD_PER_MILLION_INPUT_TOKENS / 1e6:.7f} "
              f"at ${USD_PER_MILLION_INPUT_TOKENS}/M. Wall time includes network from this machine.")


if __name__ == "__main__":
    main()
