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
6. For Xiaohongshu, load `references/xiaohongshu-search.md`: public discovery plus bounded public HTML fetch, with no login, cookies, private content, or private API. Auto-fill candidate metadata and visible text when available, never fabricate the original excerpt.
7. Run the evidence gate on a fetched or manually supplied excerpt. Keep the URL, platform, provenance status, fetch status, and publication date with the excerpt; auto-fetched text is still unverified for authenticity.
8. For interview notes, quote evidence verbatim before making a diagnosis. If no quote supports a claim, mark it unverified or omit it.
9. Emit all six PM skills in catalog order. Score only applicable V2 subdimensions with deterministic weights; mark uncovered skills/dimensions as missing and do not trust an unweighted model total. Explain the anchor match, gap, and training acceptance criteria.
10. Preserve `scored_by` after the model call: actual provider, model, prompt version, rubric version, and timestamp. Do not alter scores based on provider metadata.
11. Treat scores as coaching signals, not hiring truth. `outcome` is optional self-reported training feedback; do not infer causality, personality, intent, or hiring probability.
12. If the user enables redaction, replace only the explicitly entered company name before external model processing and label the result as best-effort redaction; never claim full anonymization.

## Resource Matrix

| Task | Read | Output boundary |
| --- | --- | --- |
| PM scoring | `pm-rubric.md`, `evidence-policy.md` | Six skills, four dimensions each, fixed-weight score or explicit missing state |
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

Before a user actively starts review, search, transcription, or file parsing, the product documentation must make clear which data stays local and which necessary fields are sent to the configured model or search provider. This is an explanation boundary, not a claim of complete anonymization.
