---
name: pm-interview-evaluation
description: Apply evidence-grounded standards to product-manager interview notes and public interview-research results. Use when reviewing PM answers, defining search relevance, assigning coaching scores, or designing follow-up practice. Do not use for hiring decisions, personality inference, or private-platform crawling.
---

# PM Interview Evaluation

Use this workflow to keep retrieval relevance, source credibility, and candidate coaching separate. Load only the references required by the task.

## Workflow

1. Load `references/pm-rubric.md` for skill IDs, dimensions, weights, and anchors.
2. Load `references/evidence-policy.md` before quoting, resolving contradictions, or handling sparse notes.
3. Load `references/diagnosis-schema.md` before emitting or migrating review JSON.
4. State the information need: target company, role, interview round, topic, and the decision the result should support.
5. Screen search snapshots for relevance only. Do not mark a result usable from a title or search summary.
6. For Xiaohongshu, load `references/xiaohongshu-search.md`: public discovery only, no login, cookies, private content, or automated post crawling. Auto-fill candidate metadata, never fabricate the original excerpt.
7. Require the original post excerpt before judging credibility. Keep the URL, platform, provenance status, and publication date with the excerpt.
8. For interview notes, quote evidence verbatim before making a diagnosis. If no quote supports a claim, mark it unverified or omit it.
9. Score only applicable PM skills with deterministic weighted subdimensions. Explain the anchor match, gap, and training acceptance criteria.
10. Treat scores as coaching signals, not hiring truth. Do not infer personality, intent, or hiring outcome from sparse notes.

## Resource Matrix

| Task | Read | Output boundary |
| --- | --- | --- |
| PM scoring | `pm-rubric.md`, `evidence-policy.md` | Six skills, four dimensions each, evidence-backed 1–5 score |
| JSON compatibility | `diagnosis-schema.md` | Preserve legacy fields; normalize new fields server-side |
| JD + question preparation | `diagnosis-schema.md`, `follow-up-strategy.md` | Use JD decomposition and public leads to prioritize questions; keep leads out of interview evidence |
| Follow-up practice | `follow-up-strategy.md` | One gap, one prompt, observable success criteria |
| Xiaohongshu search | `xiaohongshu-search.md` | Candidate discovery with query trace and manual-check status |

## Relevance Boundary

Calculate snapshot relevance from these fixed dimensions and weights:

- Company match: 30%
- Role match: 25%
- Round match: 15%
- Topic match: 15%
- Interview specificity: 10%
- Recency: 5%

The weighted score answers whether the result is worth opening for this information need. It is not a credibility score. Credibility requires the original excerpt and a separate human/AI evidence gate.

## PM Score Boundary

Use the project rubric: product sense, ownership, metrics and experimentation, execution and collaboration, structured communication, and business context. Anchor scores as follows:

- 1: no demonstrated behavior or clear mismatch
- 2: relevant point mentioned, but a key definition, action, trade-off, or result is missing
- 3: basically competent example with one important gap
- 4: specific and well-reasoned behavior with a small detail gap
- 5: evidence closes the loop across user/business context, decision, metric, result, and learning

Use fewer items when the transcript is sparse. Never invent an interviewer question, a result, a metric, or an external fact.

## Failure Handling

An empty search result must report the platform, query directions, failure or sparsity reason, and the next manual search suggestion. An incomplete transcript must lower evidence coverage and confidence; it must not be padded with default evidence. A malformed model response is rejected or normalized to the compatibility schema rather than shown as trusted output.
