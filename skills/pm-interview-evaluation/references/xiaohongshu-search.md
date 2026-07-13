# Xiaohongshu Search Boundary

Use public web search and a bounded public HTML fetch for discovery and metadata enrichment. The supported flow is:

1. Build a query with `site:xiaohongshu.com/explore` plus company, role, round, topic, and synonyms.
2. Accept only concrete post paths (`xiaohongshu.com/explore/...`, non-root `xhslink.com`, or concrete supported-platform paths); a platform homepage is not an original post candidate.
3. Keep the query trace, retrieval time, platform, relevance breakdown, and provenance status.
4. Attempt to open each concrete public URL without login, cookies, or private APIs. Auto-fill title, canonical URL, visible text, fetch status, and retrieval time when available.
5. Show fetched candidates as `auto_fetched_unverified`; show script shells, blocks, redirects, and short pages as `manual_check_required`.
6. Run credibility pre-review on a fetched or manually supplied excerpt. The pre-review may emit at most four `question_leads`; each lead must preserve whether its supporting excerpt was verified. These leads may shape JD-driven follow-up questions but are never evidence for the candidate's actual interview performance.
7. Never claim automated reading proves authenticity. Ask the user to inspect the original when the source is material or ambiguous.

Do not log in, read cookies, use private links, crawl dynamic/private content, or infer authenticity from a search snippet. If the result is empty or sparse, report the attempted queries and suggest changing company aliases, role synonyms, round names, or manually pasting a link.
