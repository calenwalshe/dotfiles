# Automation Summary

| # | Task | Auto | How |
|---|------|------|-----|
| | **DISCOVERY & INVENTORY** | | |
| 1 | Scan email for account signup confirmations | FULL | Gmail API / IMAP keyword search |
| 2 | Scan email for password reset / login alerts | FULL | Same API, different filters |
| 3 | Check emails against breach databases (HIBP) | FULL | HIBP API |
| 4 | Search people-search sites for your name/phone/address | FULL | Web scraper across 50+ known broker URLs |
| 5 | Google yourself (name, email, phone, address combos) | FULL | Search API or headless browser |
| 6 | Check domain WHOIS for personal info | FULL | WHOIS API per domain |
| 7 | Scan git repos for exposed emails | FULL | GitHub API + git log parsing |
| 8 | Check Internet Archive for your pages | FULL | Wayback CDX API |
| 9 | Score each exposure by severity | FULL | Rules engine (PII type x visibility) |
| 10 | Generate prioritized removal queue | FULL | Sort by severity score |
| 11 | Classify removable vs hard-limit exposures | FULL | Rules-based classification |
| 12 | Inventory social media accounts | SEMI | Email discovery + human confirms completeness |
| | **DATA EXPORT** | | |
| 13 | Download Google Takeout archive | FULL | Poll for ready link + download |
| 14 | Trigger Google Takeout export | SEMI | Headless browser, human auth gate |
| 15 | Trigger Facebook/Instagram data export | SEMI | Headless browser, human auth gate |
| 16 | Trigger X (Twitter) data export | SEMI | Headless browser, human auth gate |
| 17 | Verify export completeness | SEMI | Validation script + human sign-off |
| 18 | Export data from misc small services | MANUAL | Each service has unique flow, many no API |
| | **ACCOUNT DELETION** | | |
| 19 | Generate per-service deletion instructions | FULL | JustDeleteMe DB + custom lookup |
| 20 | Track deletion status per account | FULL | State database |
| 21 | Draft GDPR/CCPA deletion request emails | SEMI | Template generator, human reviews + sends |
| 22 | Delete Google account | MANUAL | Interactive auth, 2FA, security questions |
| 23 | Deactivate X account | MANUAL | Interactive auth, confirmation dialogs |
| 24 | Delete Facebook account | MANUAL | Interactive auth, "are you sure" flows |
| 25 | Delete Instagram account | MANUAL | Interactive auth |
| 26 | Delete minor/forgotten accounts | MANUAL | Each has unique flow, some need support tickets |
| | **SEARCH DE-INDEXING** | | |
| 27 | Monitor Google results for your PII | FULL | Scheduled search API queries, diff baseline |
| 28 | Check if removed results reappear | FULL | Periodic re-search |
| 29 | Submit Google removal requests | SEMI | Headless browser, CAPTCHA fallback |
| 30 | Submit Bing removal requests | SEMI | Form-based, may need auth |
| 31 | Request outdated content refresh | SEMI | Google tool, needs auth |
| 32 | Set up Google "Results about you" | MANUAL | One-time UI setup in Google account |
| | **DATA BROKER OPT-OUTS** | | |
| 33 | Identify which brokers have your data | FULL | Scrape/query 50+ known broker sites |
| 34 | Track opt-out status per broker | FULL | State database with timestamps |
| 35 | Re-check brokers for re-listing | FULL | Same scraper on cron schedule |
| 36 | Submit individual broker opt-out forms | SEMI | Bot handles web forms; human for mail/fax/phone |
| 37 | Handle broker verification emails | SEMI | Email monitor + confirmation link clicker |
| 38 | Re-submit opt-outs when re-listed | SEMI | Auto-detect, some submissions need human |
| 39 | Submit California DROP request | SEMI | State portal, likely needs identity verification |
| 40 | Handle broker verification requiring ID upload | MANUAL | Human decides what ID to share |
| | **METADATA CLEANUP** | | |
| 41 | Strip metadata from public files (PDFs, images) | FULL | ExifTool / PDF metadata batch strip |
| 42 | Enable WHOIS privacy on domains | SEMI | Script per registrar API; manual where no API |
| 43 | Rewrite git history to remove old emails | SEMI | git filter-repo scripted, human approves force push |
| 44 | Submit Internet Archive removal requests | SEMI | Draft email, human approves send |
| 45 | Switch GitHub email to no-reply | MANUAL | One-time settings click |
| 46 | Edit LinkedIn profile to remove PII | MANUAL | Human judgment on what to keep |
| | **ONGOING MONITORING** | | |
| 47 | Periodic self-search (Google, Bing) | FULL | Scheduled search agent |
| 48 | Periodic broker re-scan | FULL | Scheduled scraper |
| 49 | Alert on new PII exposure | FULL | Diff against clean baseline |
| 50 | Periodic HIBP re-check | FULL | Scheduled API poll |
| 51 | Generate periodic status report | FULL | Aggregate all monitoring data |
| 52 | Enable GPC in browsers | MANUAL | One-time browser setting |
| 53 | Re-submit removals on reappearance | SEMI | Detection auto, some submissions need human |

## Totals

| Level | Count | % |
|-------|-------|---|
| FULL — build it, run it, no human needed | 22 | 42% |
| SEMI — AI does the work, human approves at gates | 17 | 32% |
| MANUAL — human must do it, AI can only guide | 14 | 26% |
