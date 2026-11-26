# Secure sync implementation and rollout

Implemented locally on 26 November 2026. This is the first sync release, not completion of every item in SECURE_SYNC_PLAN.md. No production deployment, new cloud resources, provider migration, or security certification was performed.

## Shipped in the working tree

- Existing encrypted assessments remain in `a:<owner>`; no data migration is required. Redis Lua scripts atomically read snapshots and compare/commit changes across serverless instances. The memory backend implements the same contract for development.
- Encrypted `sync:<owner>` metadata stores a monotonic sequence, the most recent 2,000 record changes, and retry operation receipts. Cursors are encrypted/authenticated and bound to the signed-in owner.
- Create requests support `Idempotency-Key` (16–100 URL-safe characters). The server retains receipts for 24 hours, up to 2,000 operations per owner in that window. Changed content with the same key receives 409. Retrying a deleted create returns a deleted result and never recreates the assessment within the retention window. Receipts contain identifiers/digests, not previous health payloads; replays return the current record when it still exists.
- `PUT /api/assessments?id=…` requires `If-Match: <integer revision>` and returns 428 if omitted, 409 for a concurrent edit, or 404 after deletion. The UI sends revisions when deleting; legacy unversioned DELETE requests remain supported. Edits are available through the API; a comparison/editor UI is future work.
- `GET /api/assessments` returns the complete bounded snapshot, including records beyond the old 500-record truncation. `?cursor=…` returns current versions of changed records plus deleted IDs. Expired history returns 409 and the client rebuilds its snapshot. Changes are bounded by count, not the originally proposed 90-day offline window.
- Unreadable records are explicitly reported. The client warns that exports may be incomplete instead of silently treating corruption as an empty account.
- Commits check the live session inside the transaction. Account deletion atomically closes the assessment store before clearing data, preventing in-flight writes from recreating it. A minimal opaque closed-owner marker remains to reject stale requests; it contains no assessment data.
- The workstation uploads only on an explicit Save to encrypted cloud action. Its optional reference is a labeled inline field. The client holds failed saves in memory only, binds them to the account/session, prevents duplicate double-clicks, retries transient failures with backoff/jitter, and stops automatic retries on authorization or conflict errors. It stops retrying before the server's receipt window expires.
- Dashboard and workstation offer refresh, pause/resume automatic sync, retry, and discard controls. Visible tabs check every five seconds, serializing requests. Unchanged refreshes do not rebuild the table or repeat screen-reader announcements. Requests have a 15-second response-header timeout.
- Leaving the page warns about pending saves. Reloading, closing the tab, or changing session loses the in-memory pending save. Discard does not undo a request the server already received. This is not durable offline storage.
- Request body size limits now apply to both streamed and platform-parsed JSON. Sync reads and writes are rate limited. Existing CSRF and cookie/session protections remain in use.

## Verification

Run `npm test`. The suite includes account isolation, simultaneous create retries, concurrent revisions, deletion/replay, expired cursors, session revocation, account-deletion races, legacy records beyond 500, corrupted ciphertext, API headers/CSRF/body limits, and client account-switch/late-response behavior. Real Redis script tests run when `redis-server` and `redis-cli` are installed; they use a temporary local Unix socket and remove their fixture directory afterward.

Browser smoke test with a temporary synthetic account verified the accessible sync controls, keyboard pause/resume, an explicit workstation save, and the saved record appearing on the dashboard. No browser console errors were observed in those flows. This does not establish WCAG conformance; VoiceOver/NVDA, mobile/reflow, and broader assistive-technology review remain release checks.

## Deployment and recovery requirements

1. Keep the existing configured Redis and encryption keys for this release. Verify the selected Redis service accepts multi-key EVAL and supports atomic execution of these scripts. The isolated Redis test is not a verification of the production service configuration.
2. Before rollout, make a provider snapshot and securely retain the current and previous encryption keys. Exercise recovery in a separate environment with synthetic data first. Do not print or copy keys into logs.
3. Deploy API and client together. Older open tabs still use the legacy API behavior. Retain both `a:*` and `sync:*` data during rollback; never delete sync metadata while accepting writes. Rolling back to code that mutates only `a:*` makes change feeds inconsistent, so gate assessment writes during rollback and rebuild client snapshots before resuming.
4. Ensure production rejects missing storage/key configuration. Review production TLS, CSP, provider permissions, and secret access separately; local tests do not prove them.
5. Monitor 401/409/429/5xx, unreadable-record counts, latency, and Redis costs without health payloads or credentials. The implementation reads the bounded owner hash on each poll; incremental network responses do not eliminate server-side snapshot/decryption work. Load-test the 2,000-record limit and multi-device traffic before increasing quotas.
6. A backup restore must preserve deletion intent. The closed marker is only effective while present in the restored store; a separate protected deletion ledger and restore procedure are still required before promising backup-safe account erasure.

## Still to implement from the full plan

Managed PostgreSQL and row policies; managed KMS envelope keys and tested rotation; passkeys/MFA and accessible recovery; encrypted durable offline caches and device enrollment; a conflict-resolution editor; device management UI; durable audit outbox; separate deletion ledger and backup-expiry policy; measured recovery/SLO targets; independent security review and assistive-technology testing. Confirm provider, budget, region, and encryption trust model before provisioning the next infrastructure phase.

Server-side AES-GCM protects stored assessment contents, but the service can decrypt them. Do not advertise end-to-end encryption or clinical/regulatory compliance. Continue using synthetic or de-identified assessment data only.
