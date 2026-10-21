# S15 provider assessment draft — 2026-10-21

Read-only public-document review. No account, API query, key, purchase, contract acceptance or deployment. No provider approved. Funded allowance remains $0 and live request allowance remains zero. This draft is not a completed native/provider integration test.

| Candidate | Verified constraint | Eilo consequence |
|---|---|---|
| Brave Search API | Public Search price is $5/1,000 requests, with monthly credits advertised. Enterprise has separate terms. | Illustrative 1,000 calls cost $5 before any credits/tax, excluding proxy hosting and additional calls. No funded plan selected; no call may run. |
| Brave privacy | API notice allows query retention up to 90 days; enterprise ZDR is an option. Provider is US-based. | Do not claim ordinary API use is zero retention or Australia-only. A chosen plan/order, transfer/region/retention review and minimized per-query consent are prerequisites. |
| Brave rights | General terms restrict result caching except operational transient storage; separate storage rights may differ. Search does not grant rights to publisher content. | No conversation/result history, training corpus, scraped article body, thumbnail or video permission follows from a search hit. Exact product terms and attribution must be reviewed before activation. |
| Open-Meteo | Free service is noncommercial and rate limited; data attribution is CC-BY 4.0. API logs can include coordinates and last 90 days. | No silent location lookup. Require an approved commercial plan or qualifying use and attribution. The current gateway forbids location fields; this assessment does not authorize a coordinate/geolocation route. No live request. |
| Open-Meteo pricing | Commercial API uses a key/customer endpoint and servers in Europe/North America. Paid plan budgets are published; pricing FAQ says monthly hard cutoffs are not currently enforced. A payable plan amount was not established in the read page. | Eilo must enforce its own caps, keep credentials off the mobile bundle, and confirm the actual quote and deployment region before purchase. |
| Wikimedia Commons | Individual files have different credit/license requirements; the site does not own most media. | A future asset broker needs per-file author/license/source/rights metadata and revocation handling. Listing a result is not enough to fetch/play it. API retention/region/rate terms are not fully assessed here, so no media candidate is approved. |

Proposed initial scope for a later owner decision: text search only, no page scraping or media, no account identifier/history/transcript/audio sent, user previews and confirms each minimized query. A separately authorized proxy holds secrets, allowlists endpoints, limits bytes/calls/concurrency and disables redirects. Both host and UI cancel stale/dismissed requests by session/query/privacy identity; retries need fresh consent. No provider result can issue a local command. Provider and proxy retention, region, licensing, billing and attribution must all be known before any live trial. This is an engineering proposal, not authorization.

Needed to proceed: selected service/plan and terms; acceptable retention/region; funded monthly and per-trial caps; approved proxy hosting/credentials; exact attribution; then explicit permission for account/provisioning/dependency or live-query work. Continue offline conversation unchanged while blocked. S13 native-account feasibility separately needs the specified Neon/Better Auth test environment, pinned dependencies and Apple/Google credentials; none has been provisioned by this review.

Primary sources (reviewed 2026-10-21):
- [Brave product/pricing](https://brave.com/search/api/)
- [Brave API terms, dated 2026-09-01](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service)
- [Brave API privacy, updated 2026-08-25](https://api-dashboard.search.brave.com/app/documentation/general/privacy-policy)
- [Open-Meteo terms/privacy](https://open-meteo.com/en/terms)
- [Open-Meteo commercial plans](https://open-meteo.com/en/pricing)
- [Commons per-file reuse conditions](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)
