# Research protocol: live docs plus recent community evidence

Use research to find better designs, not to produce a popularity leaderboard. A focused question-design task can reuse fresh findings already in context. For a new opportunity scan, refresh both lanes below.

## Official lane

Start at https://docs.typesafe.ai/llms.txt. Fetch relevant pages as Markdown by appending `.md`, or use normal pages if Markdown fails. Read the primitive and closest cookbook before choosing an architecture. Refresh models, pricing, context/rate limits, known limitations, and native API/SDK shape. TypeSafe's own skill at https://github.com/typesafe-ai/skills is a useful current reference for API and primitive basics.

Do not blend API dialects. Native TypeSafe uses Noul; a gateway may name its corresponding primitive Boolean and expose different fields. Check the exact provider/version selected by the user. A model alias can change behavior; identify the resolved version in measured results.

## Community lane

If last30days is installed, read its SKILL.md and use its own runtime/preflight/query-plan process. Choose the lookback from how much is being published. Start at about seven days (three during a launch or release week, when volume is high). If that yields fewer than a handful of first-hand sources, widen to fourteen and then thirty days rather than padding findings with reposts. Record the actual start and end dates and the retrieval time. Resolve Jev to TypeSafe AI (typesafe.ai, @typesafeai, typesafe-ai GitHub organization) to avoid unrelated results.

Useful angles:

- Jev TypeSafe first-hand builds and surprising applications.
- Jev TypeSafe questions, primitives, state design and batching.
- Jev TypeSafe measured latency/cost versus LLMs, accuracy losses and failures.

Prefer original authors, runnable repos, exact questions and clearly scoped tests. Follow links from social discussion to code and benchmark methods. Read both successful and unsuccessful designs. Community discovery can surface a new pattern even without a benchmark; label it accordingly.

Inspect source status: rate-limited or failed does not mean nobody discussed the topic. Supplements should fill missing depth with primary author blogs/repos and official docs. Check publication dates yourself: engine date filters or inferred timestamps can admit older items. Older sources may explain a concept but must not be labeled a discovery from the current window. If the engine is absent, available public search is a disclosed fallback, not a last30days run.

## Evidence record

For each useful discovery retain: original URL, author, publication/test date, use case, question/primitive shape, observed result, baseline/model/workload, limitation, and transferable lesson. No need to copy full articles or chatter.

Use these labels:

- **Official contract:** documented interface/limits, subject to version changes.
- **Vendor benchmark:** measured by the provider, with its workload and comparator.
- **Author-reported measurement:** first-hand numbers you did not reproduce.
- **Demo/code:** evidence of an implementation pattern, not its general performance.
- **Proposed adaptation:** your design inspired by the evidence, not an existing capability result.

Ask what changes in the proposed application: more candidates, more frequent checks, less blocking latency, fewer tokens, better uncertainty handling, or less review work. If nothing meaningful transfers, omit the finding. Never turn repost counts, stars, subjective speed impressions or schema validity into accuracy evidence.

When you report findings, keep each source's date next to it so older research is never presented as current. [community-discoveries.md](community-discoveries.md) shows the format.
