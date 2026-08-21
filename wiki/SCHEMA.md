# Wiki Schema — AI-News-Bot

## Domain
Autonomous AI news intelligence system (Python). Sources: RSS, Reddit, Twitter/Nitter,
YouTube, Hacker News, arXiv. Multi-provider LLM summarization with automatic fallback.
Telegram delivery. This wiki is the project's long-term memory (Karpathy LLM-Wiki pattern),
managed by the Hermes Autonomous Engineering Session (HAES) cron job.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `llm-provider-fallback.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- **Provenance markers:** On pages synthesizing 3+ sources, append `^[raw/...]` at the end of
  paragraphs whose claims trace to a specific raw source. Optional on single-source pages.

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low        # how well-supported the claims are
contested: true                        # set when the page has unresolved contradictions
contradictions: [other-page-slug]      # pages this one conflicts with
---
```

## Tag Taxonomy
- System: architecture, pipeline, config, deployment, ci
- Components: module, fetcher, llm, formatter, sender, dispatcher, db, dedup
- Sources: rss, reddit, twitter, youtube, hackernews, arxiv
- Quality: testing, technical-debt, coverage, bug
- Meta: decision, roadmap, convention, backlog, comparison

Rule: every tag on a page must appear in this taxonomy. Add new tags here FIRST, then use.

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside the domain
- **Split a page** when it exceeds ~200 lines
- **Archive a page** when its content is fully superseded — move to `_archive/`

## Update Policy
When new information conflicts with existing content:
1. Check dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark `contradictions: [page-name]` and `contested: true`
4. Flag for user review in the lint report

## Precedent
This wiki supersedes `.hermes/repo-memory.md` (last updated 2026-07-12, stale — reported
145 tests; current state is 199 tests + CI gate as of 2026-08-20). The `.hermes/repo-memory.md`
file is retained only as a pointer and is no longer the source of truth.
