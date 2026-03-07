# What Cannot Be Removed (and Why)

## Hard Limits

### Public Records
Government records — property deeds, court filings, voter registration, business filings — are generally exempt from deletion requests under all major privacy laws. These are considered public interest data.

### Breach Datasets
Data leaked in breaches exists in distributed copies across forums, paste sites, and dark web marketplaces. No legal mechanism has practical reach over these copies. Breached credentials can be rotated, but exposed PII (SSN, DOB, addresses) cannot be "unbreached."

### Third-Party Reposts
Content reposted, screenshotted, or syndicated by others is controlled by those third parties. Deleting the original does not cascade to copies. Each copy requires its own removal request to a different entity.

### Cached/Archived Copies
- **Search engine caches**: Temporary, but refresh timing varies
- **Internet Archive**: Reviews removal requests case by case, does not guarantee compliance
- **CDN caches**: Clear when TTL expires or origin is removed
- **Corporate archives**: Internal copies at companies that ingested your data

## Soft Limits (Technically Possible but Practically Difficult)

### Broker Re-Listing
Data brokers re-scrape public records and other sources continuously. Removed listings frequently reappear within weeks or months. This is the primary reason one-time cleanup fails — ongoing monitoring is required.

### Old Git Commits
Switching to a no-reply email prevents new commits from exposing your email, but existing commits tied to your real email remain in repository history. Rewriting git history is possible but disruptive and may not propagate to all forks.

### Compliance Records
Companies that process deletion requests may retain minimal records proving they handled the request. This is legally permitted and practically unavoidable.

### Social Graph Inference
Even after account deletion, platforms may retain anonymized or aggregated data. Your connections, behavioral patterns, and metadata may persist in others' data or in aggregate models.

## The Realistic Ceiling

**"Substantially harder to find, profile, and broker"** — not "fully erased from the internet."

The strongest outcome achievable:
- Major search engines return minimal personal results
- People-search sites show no current listings (requires ongoing monitoring)
- Data broker records are suppressed (requires ongoing re-deletion)
- Social media presence is removed at source
- Domain/git metadata is cleaned up
- Forward-looking collection is minimized

What remains despite best efforts:
- Public government records
- Historical breach data
- Third-party copies and screenshots
- Some archived web content
- Compliance/audit records at companies that processed deletions
