# Xiaohongshu Search Boundary

Use public web search for discovery only. The supported flow is:

1. Build a query with `site:xiaohongshu.com/explore` plus company, role, round, topic, and synonyms.
2. Keep the query trace, retrieval time, platform, relevance breakdown, and provenance status.
3. Show candidates as `manual_check_required` or `needs_review`.
4. Ask the user to open the original post and paste a relevant excerpt.
5. Only then run credibility pre-review; never claim the search summary is the post content.

Do not log in, read cookies, use private links, crawl the platform, or infer authenticity from a search snippet. If the result is empty or sparse, report the attempted queries and suggest changing company aliases, role synonyms, round names, or manually pasting a link.
