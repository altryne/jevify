# Patterns worth looking for

These are composable starting points. Explore the current [use-case map](https://docs.typesafe.ai/concepts/use-case-map) and cookbooks before designing. “Can an LLM do this?” is often yes; the opportunity is whether cheaper, faster repeated decisions change the product.

| Pattern | Question design and code composition | Where the benefit could come from |
|---|---|---|
| Route work to a handler, tool, skill or model | Choice over concrete handlers; separate complexity Score and evidence-sufficiency check. Code applies policy, fallback and permissions. | Avoid a generative router on every request; reserve expensive models for cases that need them. |
| Retrieve many useful items | Noul per candidate for inclusion, or Score per candidate for graded utility; batch over shared query/state. Code enforces diversity and context budget. | Inspect a wider pool or keep retrieval off the latency-critical path. |
| Check work continuously | One Noul per defined defect, or distinct quality Scores. A generator revises only flagged work; rerun checks on the revision. | Feedback while an artifact is being written, rather than a slow end-only review. |
| Extract by selection | Parser/generator proposes possible values with source IDs; Choice picks the intended ID or missing/ambiguous. Code copies and normalizes. | Remove expensive free-form extraction or reduce its retries without inventing values. Candidate recall remains essential. |
| Verify extraction or citations | Given source + candidate claim/field, Noul for support or Choice supported/contradicted/not established. | Cheap verification of many fields, with a stronger model only on failures. Source support is not universal truth. |
| Recover document structure | Classify line/block roles and whether adjacent spans belong together; code reconstructs layout from original content. | Produce useful transformed documents without regenerating every token. Preserve source order/content unless intended otherwise. |
| Semantic find | Enumerate source spans; ask per-span relevance or choose one if exactly one is desired. Code returns exact source excerpts. | Natural-language search inside documents, logs or code, with stable IDs. |
| Entity matching | Score each proposed pair using concrete merge/review/non-match criteria; code applies uniqueness/business constraints. | Judge fuzzy pairs cheaply after deterministic blocking/retrieval. Avoid all-pairs explosion. |
| Reusable quality features | Separate Scores for independent properties; code changes weights or a trained small model consumes the features. | Re-rank or personalize without redoing unchanged judgments. Hard requirements stay separate. |
| Interactive state interpretation | Present named current facts and candidate actions; Choice for a bounded next step, with success/block checks. | Faster small decisions in games, home workflows, browser/agent loops. Fresh state and external execution still matter. |
| Sensory evidence hybrid | An audio/vision/frontend detector supplies semantic observations and candidates. Jev adjudicates those alongside text context. | Combine sensory evidence with task intent; native image/audio understanding is not implied. |

Official worked references:

- [Function calling](https://docs.typesafe.ai/cookbooks/function_calling), [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out), [skill selection](https://docs.typesafe.ai/cookbooks/skill_suggestion).
- [Reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe), [semantic find](https://docs.typesafe.ai/cookbooks/semantic_find), [hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification).
- [Candidate extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), [citation checks](https://docs.typesafe.ai/cookbooks/citation_check), [extraction cascade](https://docs.typesafe.ai/cookbooks/sde_cascade).
- [Structure recovery](https://docs.typesafe.ai/cookbooks/autoformat), [entity alignment](https://docs.typesafe.ai/cookbooks/entity_alignment), [feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery).

For every adaptation, produce real questions and state requirements. A list of these pattern names is not a completed Jevify assessment. Keep generation for novel content and multi-step reasoning when it is needed. Compute exact numbers, times, identifiers and constraints in code. Serialized raw spectra or embeddings do not acquire semantic meaning merely by fitting JSON; test a meaningful frontend representation first.
