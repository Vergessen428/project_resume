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

Each of the six PM skills has four weighted dimensions. The backend computes `exact_score` only from `observed`, `contradicted`, or `unverified` dimension scores; `missing` and `not_applicable` dimensions are always unscored, even when a model supplies a number. It rounds to the existing 1–5 `score`, then computes the 0–100 `coach_score` as a training signal. A separate evidence profile evaluates specificity, ownership, causality, result quality, reflection, and resilience under follow-up questions, so a high capability score is not confused with a well-supported answer. Invalid skill or dimension IDs are discarded or downgraded during normalization.

## Compatibility

`schema_version` is `2.1`. Existing `score`, `evidence`, `diagnosis`, and string `next_practice` fields remain readable. New fields are bounded, validated, and safe to omit. `scored_by` is factual provider/model/prompt/rubric provenance, not a score adjustment. `action_plan` items carry stable `action_key`/`id`, source skill/gap and interview metadata, plus the persisted training lifecycle; rerunning a review must merge these items without deleting attempts or acceptance state. Static demo data follows the same names but is explicitly synthetic.

Interview `outcome` is optional self-reported training feedback. It must not be used to infer hiring probability or score causality. Memory must expose sample counts and model comparability before showing any outcome grouping.

## Maintenance

When adding a skill, update the rubric, schema examples, backend catalog, static fixture, API tests, and UI. Keep platform-specific source handling in research grounding, not in the PM score rubric.
