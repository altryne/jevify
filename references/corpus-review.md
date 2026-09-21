# Review a large conversation archive

Use this workflow to extract goals, feedback, requirements, or lessons across many conversations. Keep the corpus and intermediate results in task files. Bring only metadata, bounded samples, and selected originals into the reasoning context. A full-corpus read requires the user's explicit request for that exceptional approach.

## Preserve the source before judging it

1. Parse messages in code. Write a manifest with the source hash, conversation ID, message ID, recorded role, timestamp, and exact location. Preserve quoted text and machine wrappers as separate fields when the format identifies them. A user-channel wrapper is not proof that every sentence is the person's own instruction.
2. Build bounded units around one message or one coherent passage. Keep the speaker's text separate from neighboring context. Carry a short relevant predecessor when a phrase such as "that change" needs it. When splitting a message, keep its parent ID and exact offsets.
3. Print only record counts, role counts, size ranges, and a small sample. Check that every source message maps to units or has an explicit exclusion reason. A short question, complaint, or positive reaction remains eligible.

Use recorded roles as facts. Ask Jev about the meaning of a message, not whether a message recorded as user was actually written by the assistant. If the export does not identify the author, retain `unknown` and resolve the source before attributing a requirement.

## Ask separate questions over the same state

For each user message, ask independently whether it expresses:

- A desired outcome, ambition, or direction, including one phrased as a question.
- Friction, a correction, or a constraint on the current behavior.
- A positive reaction that reveals which behavior worked.
- A speculative option or request for discussion, rather than an instruction to implement.

Batch these questions over shared, bounded state. A message can qualify for several categories. Avoid a single "most important durable rule" question: it asks Jev to discard distinctions before recurrence and context are known. Treat assistant proposals and completion claims separately; verify a claimed result against actual evidence before using it as fact.

[message-signals.json](../assets/message-signals.json) is a runnable synthetic request pack. Run it with `scripts/run_cases.py assets/message-signals.json --dry-run` from the skill directory, or resolve both paths from the task directory. It demonstrates the question shape, not a universal threshold. For real work, generate these questions over the actual units and save all returned probabilities, question versions, source IDs, and failures.

## Preserve recurrence across chunks

Maintain one file-backed evidence ledger across batches. Each candidate theme needs source IDs, supporting excerpts or offsets, distinct conversation counts, contrary evidence, and unresolved references. Deduplicate overlapping windows by parent message ID before counting recurrence. Preserve isolated high-consequence constraints even when their count is one.

Start themes from bounded samples and selected originals. Use per-message Nouls to map further evidence to each theme, with an unmatched category or review path for new themes. A Choice may assign one primary theme for navigation, but it must not erase other applicable themes. Code counts occurrences; Jev judges semantic relationships. Read a small unmatched sample each batch and revise the theme set when it reveals a new concern.

## Check misses and repair the question

Inspect a bounded sample from each signal category, conversation, and score band, including low-ranked and uncertain results. Include short messages and boundary splits. Retrieve the exact original and only the neighbors needed to interpret it. When the task requires exhaustive coverage, account for every required source unit; sampling alone cannot prove that nothing was missed.

When a result is wrong, inspect the state, question, answer, and consuming code together. Check whether the target text was present, the role was preserved, a reference was unresolved, or the question collapsed several meanings. Revise the smallest failing part and rerun the affected units. Try the revised question on a few untouched cases too. Repeated failures may need a different unit or a focused reasoning read; lowering the threshold alone does not repair a bad question.

Keep request failures and malformed answers marked `unjudged`. Recover them or report the missing coverage. A low score is still a judgment; it is not proof that the text contains no useful evidence.

## Carry the evidence into the final result

Before finalizing, map each retained theme to a paragraph, rule, or action in the draft. For a theme you omit, record why in the local ledger. Check especially that positive feedback, recurring friction, and broad goals survived alongside concrete fixes. Record contradictions and scope limits rather than turning every idea into a mandatory requirement.

A compact completion report names the corpus coverage, unresolved or unjudged units, sampled misses, and source pointers used. Report actual returned tokens and elapsed time if useful. The artifact must satisfy the user's original task; a ranked list alone does not finish the review.
