# PM Interview Evaluation Skill Specification

## Scope

This skill evaluates PM interview notes for training. It does not simulate a live interview, predict hiring outcomes, or decide whether a public post is authentic.

## Evidence Model

Every diagnostic claim has one of five statuses: `observed`, `missing`, `contradicted`, `not_applicable`, or `unverified`. `observed` and `contradicted` require a short verbatim transcript quote. Missing evidence is explicit and lowers confidence.

Search relevance and source credibility are separate:

- Relevance asks whether a public search candidate is worth opening for the current company, role, round, and topic.
- Credibility asks what the opened original excerpt can support.
- A search citation can prove URL provenance, but it cannot prove the post contents.

## Deterministic Scoring

Each of the six PM skills has four weighted dimensions. The backend computes `exact_score` from applicable, evidence-backed dimension scores, rounds to the existing 1–5 `score`, then computes the 0–100 `coach_score` as a training signal. A separate evidence profile evaluates specificity, ownership, causality, result quality, reflection, and resilience under follow-up questions, so a high capability score is not confused with a well-supported answer. Invalid skill or dimension IDs are discarded or downgraded during normalization.

## Compatibility

`schema_version` is `2.0`. Existing `score`, `evidence`, `diagnosis`, and string `next_practice` fields remain readable. New fields are bounded, validated, and safe to omit. Static demo data follows the same names but is explicitly synthetic.

## Maintenance

When adding a skill, update the rubric, schema examples, backend catalog, static fixture, API tests, and UI. Keep platform-specific source handling in research grounding, not in the PM score rubric.
