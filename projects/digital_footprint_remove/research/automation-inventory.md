# Automation Inventory: What AI Can Build vs What Stays Manual

## Legend

- **AUTOMATE** — can build a tool/agent to handle this end-to-end
- **SEMI-AUTO** — AI can do the heavy lifting but needs human input at key gates
- **MANUAL** — requires human identity verification, legal authority, or platform UI interaction

---

## Phase 1: Discovery & Inventory

### Account Discovery

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Scan email inbox for account signup confirmations | **AUTOMATE** | Gmail API / IMAP search for "welcome", "verify", "account created" patterns | Email parser agent — extract service name, date, email used |
| Search email for password reset / login notifications | **AUTOMATE** | Same email API, different keyword patterns | Same agent, different filter set |
| Cross-reference with known breach databases (HIBP) | **AUTOMATE** | HIBP has a public API | API client — input emails, get back breached services + data types |
| Search for your name/email/phone across people-search sites | **AUTOMATE** | Web scraping / search API queries | Scraper agent hitting known broker sites (Spokeo, WhitePages, BeenVerified, etc.) |
| Google yourself (name, email, phone, address variations) | **AUTOMATE** | Search API or headless browser | Search agent — structured queries, parse results, flag PII matches |
| Check domain WHOIS records for personal info exposure | **AUTOMATE** | WHOIS API lookups | Simple API script per domain |
| Scan git repos for exposed emails | **AUTOMATE** | `git log` parsing, GitHub API | Script to enumerate repos and extract commit emails |
| Check Internet Archive for your controlled pages | **AUTOMATE** | Wayback Machine API (CDX) | API query per domain/URL you owned |
| Inventory social media accounts (active + dormant) | **SEMI-AUTO** | Can find many via email search, but user needs to confirm completeness | Discovery agent + human review checklist |

### Exposure Assessment

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Score each exposure by severity (PII type, visibility) | **AUTOMATE** | Classification rules on discovered data | Scoring engine — weight by data type (SSN > address > email) and visibility (Google page 1 > broker > archive) |
| Generate prioritized removal queue | **AUTOMATE** | Sort by severity score | Output of scoring engine |
| Identify which exposures are removable vs hard limits | **AUTOMATE** | Rules-based: public records = hard, broker listings = removable | Classification engine referencing limitations.md |

---

## Phase 2: Data Export (Before Deletion)

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Trigger Google Takeout export | **SEMI-AUTO** | Can navigate the flow programmatically, but Google may require interactive auth | Headless browser with human auth gate |
| Download Takeout archive when ready | **AUTOMATE** | Download link from email/API | Polling + download agent |
| Trigger Facebook/Instagram data download | **SEMI-AUTO** | Platform UI flow, auth required | Headless browser, human auth gate |
| Trigger X (Twitter) data export | **SEMI-AUTO** | Platform UI flow, auth required | Same pattern |
| Export data from smaller/misc services | **MANUAL** | Each service has unique flow, many have no API | Human clicks through each one |
| Verify export completeness | **SEMI-AUTO** | Can check file sizes/contents, but user confirms nothing critical is missing | Validation script + human sign-off |

---

## Phase 3: Account Deletion

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Delete Google account | **MANUAL** | Requires interactive identity verification (password, 2FA, security questions) | Human must complete — too many auth gates |
| Deactivate X account | **MANUAL** | Same — interactive auth, confirmation dialogs | Human must complete |
| Delete Facebook account | **MANUAL** | Same — interactive auth, "are you sure" flows | Human must complete |
| Delete Instagram account | **MANUAL** | Same | Human must complete |
| Delete minor/forgotten accounts | **MANUAL** | Each has unique deletion flow, some require email support tickets | Human, possibly guided by generated instructions |
| Generate per-service deletion instructions | **AUTOMATE** | JustDeleteMe database + custom research | Agent that looks up deletion URLs and steps per service |
| Track deletion status (confirmed, pending, failed) | **AUTOMATE** | State tracking database | Simple tracker with status per account |
| Send deletion request emails to services without self-serve | **SEMI-AUTO** | Can draft and send GDPR/CCPA deletion emails | Email template generator + send with human approval gate |

---

## Phase 4: Search De-Indexing

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Set up Google "Results about you" monitoring | **MANUAL** | Requires Google account authentication and UI interaction | Human sets up once |
| Submit Google removal requests for specific URLs | **SEMI-AUTO** | Can automate form submission, but Google may require auth/CAPTCHA | Headless browser with human CAPTCHA fallback |
| Monitor Google search results for your PII | **AUTOMATE** | Periodic search API queries | Monitoring agent — scheduled searches, diff against baseline |
| Submit Bing content removal requests | **SEMI-AUTO** | Similar to Google — form-based, may need auth | Same approach |
| Check if removed results reappear | **AUTOMATE** | Periodic re-search | Same monitoring agent |
| Request outdated content refresh after source deletion | **SEMI-AUTO** | Google has a tool for this, needs auth | Headless browser |

---

## Phase 5: Data Broker Opt-Outs

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Identify which brokers have your data | **AUTOMATE** | Scrape/query known broker sites for your name/address/phone | Discovery scraper — hit 50+ known broker URLs |
| Submit California DROP request | **SEMI-AUTO** | State portal, likely requires identity verification | Human submits once; track status automatically |
| Submit individual broker opt-out requests | **SEMI-AUTO** | Many brokers have web forms; some require email/mail/fax | Bot can handle web forms; human handles mail/fax/phone |
| Handle broker verification emails ("confirm your removal") | **SEMI-AUTO** | Can monitor inbox and click confirmation links | Email monitor agent + link clicker |
| Handle broker verification requiring ID upload | **MANUAL** | Requires human judgment on what ID to share | Human decision — some brokers ask for too much |
| Track opt-out status per broker | **AUTOMATE** | State database | Tracker with per-broker status + timestamps |
| Re-check brokers for re-listing (ongoing) | **AUTOMATE** | Same scraper on a schedule | Cron job — monthly re-scrape of all broker sites |
| Re-submit opt-outs when re-listed | **SEMI-AUTO** | Same submission flow, may hit new CAPTCHAs | Automated with human fallback |

---

## Phase 6: Metadata Cleanup

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Enable WHOIS privacy on domains | **SEMI-AUTO** | Most registrars have API or dashboard toggle | Script per registrar API; manual for registrars without API |
| Switch GitHub email to no-reply | **MANUAL** | One-time settings change in GitHub UI | Human clicks — 30 seconds |
| Rewrite git history to remove old emails | **SEMI-AUTO** | `git filter-branch` or `git filter-repo` scripted, but needs human decision on which repos + force push approval | Script generator + human approval for each repo |
| Submit Internet Archive removal requests | **SEMI-AUTO** | Email-based process; can draft and send, but review is manual on their end | Draft agent + human send approval |
| Remove personal info from LinkedIn (if keeping account) | **MANUAL** | UI interaction, judgment calls on what to keep | Human edits profile |
| Scrub metadata from publicly shared files (PDFs, images) | **AUTOMATE** | ExifTool / PDF metadata stripping | Batch processing script |

---

## Phase 7: Ongoing Monitoring & Prevention

| Task | Classification | Why | Build Approach |
|------|---------------|-----|----------------|
| Enable GPC in browsers | **MANUAL** | One-time browser setting | Human clicks — 10 seconds |
| Periodic self-search across Google/Bing | **AUTOMATE** | Search API + result parsing | Scheduled monitoring agent |
| Periodic broker re-scan | **AUTOMATE** | Same scraper infrastructure | Scheduled scraper |
| Alert on new PII exposure | **AUTOMATE** | Diff new results against known-clean baseline | Alerting layer on top of monitoring |
| Periodic HIBP re-check for new breaches | **AUTOMATE** | HIBP API polling | Scheduled API check |
| Re-submit removal requests when things reappear | **SEMI-AUTO** | Automated detection, some submissions need human | Detection = auto, submission = semi-auto (same as phase 5) |
| Generate periodic status report | **AUTOMATE** | Aggregate all monitoring data | Report generator — what's clean, what reappeared, what's new |

---

## Summary Scoreboard

| Category | AUTOMATE | SEMI-AUTO | MANUAL |
|----------|----------|-----------|--------|
| Discovery & Inventory | 8 | 1 | 0 |
| Data Export | 1 | 4 | 1 |
| Account Deletion | 2 | 1 | 5 |
| Search De-Indexing | 2 | 3 | 1 |
| Data Broker Opt-Outs | 3 | 4 | 1 |
| Metadata Cleanup | 1 | 3 | 2 |
| Ongoing Monitoring | 5 | 1 | 1 |
| **Totals** | **22** | **17** | **11** |

## What To Build (Priority Order)

### High-Value Automation Targets (build these first)

1. **Discovery Agent** — email inbox scanner + HIBP check + Google/broker self-search + WHOIS + git email scan. This is the foundation everything else depends on, and it's almost entirely automatable.

2. **Broker Scanner & Opt-Out Bot** — scrape 50+ known broker/people-search sites, detect listings, submit opt-out forms where possible, track status. This is the highest-volume repetitive work and the area where paid services (DeleteMe, Incogni) charge $100-200/yr.

3. **Monitoring Agent** — scheduled re-scans of search engines, brokers, and HIBP. Alert on reappearance. This is the "never done" layer that makes one-time cleanup actually stick.

4. **Status Dashboard / Report Generator** — aggregate all discovery, removal, and monitoring data into a single view. Track what's clean, what's pending, what reappeared.

### Human-Gated Tasks (build guides, not bots)

5. **Deletion Playbook Generator** — for each discovered account, generate step-by-step deletion instructions (leveraging JustDeleteMe data + custom research). Human executes but bot prepares the path.

6. **GDPR/CCPA Request Drafter** — template-based email generator for services without self-serve deletion. Human reviews and sends.

### Stays Manual (no point automating)

- Account deletions on major platforms (auth gates make automation fragile and risky)
- One-time browser/GitHub settings changes
- Identity document decisions for broker verification
- LinkedIn/social profile editing
