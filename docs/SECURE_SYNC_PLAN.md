# Secure, accessible cloud sync plan

Status: phased implementation started, 26 November 2026. See [SECURE_SYNC_IMPLEMENTATION.md](SECURE_SYNC_IMPLEMENTATION.md) for implemented behavior, verification, rollout requirements, and remaining work. Cloud infrastructure has not been changed.

## Outcome and scope

Give every supported user a private account with reliable access to their assessments across devices. Cloud sync is opt-in; users can continue locally. Basic security, export, deletion, and accessibility are available to everyone. “Everyone” means inclusive access, not public access to records.

Start with personal accounts and synthetic or de-identified assessments, consistent with the README. Shared clinical workspaces, identifiable patient records, and raw report uploads require a separate product and data-governance review before inclusion. Do not claim clinical suitability or regulatory certification from this architecture.

## What exists

Repository inspection shows:

- `api/_lib/auth.js`: server-side sessions, HttpOnly cookies, CSRF checks, rate limiting, and audit helpers.
- `api/_lib/crypto.js`: scrypt passwords and AES-256-GCM assessment encryption bound to user and record IDs. The server holds decryption keys; this is not end-to-end encryption.
- `api/_lib/db.js`: production Redis REST storage; development memory/file storage.
- `api/assessments.js`: create, list, and delete. Listing returns at most 500 items despite a 2,000-record allowance. There is no exposed revision, sync cursor, idempotency contract, or deletion feed. Unreadable records are currently skipped.

These observations are planning inputs, not a completed security audit or proof of deployed configuration.

## Proposed architecture

Keep the existing web/API boundary. Introduce a managed transactional PostgreSQL database as the durable source for accounts, assessments, revisions, sync operations, and deletion markers. Retain Redis for short-lived sessions and rate limits. Select the provider and region after checking budget, backup capability, key-management integration, and intended user geography; do not provision services as part of this plan.

Clients communicate with authenticated APIs only. Database credentials and encryption keys never reach the browser. Enforce ownership on every API request and add database row policies as defense in depth, using request-scoped identity and a constrained application role. Infrastructure admins do not automatically receive health-record access.

Core records:

| Entity | Required fields or behavior |
| --- | --- |
| Assessment | UUID, owner ID, ciphertext, key version, revision, schema/model version, server timestamps, deleted timestamp |
| Sync operation | Owner ID + operation UUID unique, payload digest, committed result; bounded retention |
| Change log | Owner-scoped ordered sequence, record ID, revision, deletion flag; written atomically with mutations |
| Device | Owner ID, revocable session association, last successful cursor, display name |
| Audit event | Actor, action, resource ID, outcome, timestamp; no assessment inputs or tokens |

## Sync correctness

1. A client saves a draft and queues an operation with a stable UUID, record UUID, and expected revision. Persistent offline storage requires explicit trusted-device opt-in; shared-device mode keeps drafts in memory.
2. The server derives ownership from the session, validates size/schema, and atomically checks revision, applies the change, records the operation result, and appends the change event. A replay returns the prior result; reuse with different content is rejected.
3. Clients pull bounded pages using an opaque owner-scoped cursor. Advance the cursor only after safely applying the page locally. Use an ordered commit-safe change feed so overlapping transactions cannot cause skipped events.
4. Conflicting assessment edits return a conflict response and preserve both versions for user resolution. Never silently overwrite health-related inputs. Assessments retain the model version used; sync does not silently recalculate results.
5. Deletions create tombstones. Stale edits cannot resurrect deleted records. Keep change history/tombstones for an initial 90-day offline window; older devices must rebuild their snapshot and explicitly reconcile pending work before uploading.
6. Retry transient failures with exponential backoff and jitter. Respect rate-limit delays; pause on authentication errors and preserve pending changes. Realtime notifications may prompt a pull but are never the source of truth.
7. Scope every local queue to its account. Account switches cannot upload another account's drafts. On logout, offer an explicit choice for unsynced drafts before clearing local state; never label queued data as cloud-saved.

Expose clear states: Saved on this device, Syncing, Synced, Offline, Sign in to resume, Conflict needs review, and Storage full. Show last successful sync and an accessible Retry action.

## Security and privacy requirements

- Prefer passkeys, with accessible password-manager-compatible fallback and recovery. Require phishing-resistant MFA for privileged accounts. Protect enrollment, recovery, email changes, export, and account deletion with appropriate reauthentication and session revocation.
- Default new accounts to an ordinary personal-user role. A self-selected profession must never grant clinical or administrative privileges.
- Use HTTPS, secure cookies, CSRF protection, strict origin validation, restrictive CSP, dependency checks, request/body limits, and distributed abuse controls. Validate OAuth issuer/provider configuration and account-linking behavior before launch.
- Move from environment-only data keys toward managed KMS envelope encryption with versioned keys and authenticated owner/record metadata. Design rotation, bulk re-encryption, backup key retention, and recovery together. Keep separate production and test keys.
- Encrypt persistent desktop caches using OS-protected keys. Browser storage encryption does not protect against active same-origin script compromise; minimize caching, prevent XSS, and make shared-device mode easy to choose.
- Explain that the service can decrypt cloud records. If server-blind end-to-end encryption becomes a requirement, treat device enrollment, lost-key recovery, search, sharing, and support limitations as a separate design decision before promising it.
- Upload only explicitly selected structured data. Keep raw lab reports local in the initial release. Exclude health values, names, tokens, and report contents from telemetry, URLs, notifications, and analytics.
- Provide export, device/session revocation, pause sync, delete individual records, and delete account. Pausing sync does not delete existing cloud copies; explain this in the interface.
- Account deletion immediately blocks sessions and new writes, then removes primary data through a tracked job. Define and disclose backup expiry; maintain a protected deletion ledger so restored backups cannot reactivate deleted accounts. Remote revocation cannot erase copies on a disconnected device.
- Replace best-effort-only audit handling for sensitive operations with a durable transactional outbox and restricted audit storage. Alert on failures without logging sensitive payloads.

## Accessible and affordable experience

Target WCAG 2.2 AA across onboarding, login, recovery, sync status, conflicts, export, and deletion. Provide keyboard operation, visible focus, semantic labels, screen-reader announcements, adequate contrast, zoom/reflow, reduced motion, and status indicators that do not depend on color.

Allow password managers and paste, including verification codes; avoid puzzle-only authentication. Use plain language, localization-ready text, responsive screens, and low-bandwidth incremental sync. Do not require a smartphone or biometric hardware as the sole account-access path. Test manually with keyboard, VoiceOver, and NVDA in addition to automated checks.

Set transparent quotas and warn before reaching them. Quota or billing failures must preserve existing data and permit export/deletion. Confirm operating costs before committing to free storage limits.

## Delivery sequence and acceptance gates

| Phase | Deliverable | Gate |
| --- | --- | --- |
| 1: Foundations | Data inventory, threat model, provider/region decision, ownership schema, account-role cleanup, recovery design | Two-account isolation tests; agreed retention and encryption trust model |
| 2: Cloud durability | Transactional storage, encrypted records, key management, pagination, migration tooling, backups | Counts and decrypted-content checks reconcile; failed records quarantined and reported; restore and key-rotation drills pass |
| 3: Sync | Outbox, idempotency, revisions, change feed, tombstones, account-scoped queues | Duplicate retries, concurrent edits, reordered responses, offline delete/edit, expired cursors, device logout, and account switching pass |
| 4: Inclusive controls | Accessible onboarding, sync states, conflict resolution, privacy/device controls | Manual assistive-technology checks; slow-network and shared-device scenarios pass |
| 5: Release | Small opt-in pilot, monitoring, incident runbook, independent security review | No unresolved critical/high security findings; measured recovery and sync targets met |

Migration: back up and retain the original decryption keys; temporarily gate writes during a controlled migration; preserve user IDs and map old record IDs; validate every migrated record; switch reads and writes together. Rollback must reconcile any writes accepted after cutover before reverting. Never silently discard records that fail decryption.

Initial engineering targets, subject to pilot measurement: 95% of online changes visible on a second active device within 5 seconds; no duplicate records or silent overwrites in failure-injection tests; backup recovery point within 15 minutes and recovery within 4 hours. Validate targets against the selected service tier. Alert on sync backlog, decryption errors, authorization failures, and backup failures. Assign an incident owner before launch.

Before implementation, confirm expected active users, storage budget, launch regions, and whether server-readable encrypted storage meets the intended privacy promise. These are provisioning decisions; they do not prevent building the schema, protocol, and test fixtures.

## References

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): deny by default and validate permissions on every request.
- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/): accessibility target.
- [W3C accessible authentication guidance](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum): accessible sign-in and password-manager support.
