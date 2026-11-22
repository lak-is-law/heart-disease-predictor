# Deploying the portal

The site is static (`portal/`) plus serverless functions (`api/`) on Vercel.

## 1. Database

Add **Upstash for Redis** from the Vercel Marketplace (Storage tab). It sets `UPSTASH_REDIS_REST_URL`
and `UPSTASH_REDIS_REST_TOKEN` (legacy `KV_REST_API_URL` / `KV_REST_API_TOKEN` also work).
Without a database the API refuses requests in production instead of falling back to memory.

## 2. Environment variables

| Name | Value |
| --- | --- |
| `SESSION_SECRET` | 32+ random characters (`openssl rand -base64 48`). Keys the hashes used for emails and IPs. Changing it signs everyone out and breaks email lookups, so treat it as permanent. |
| `DATA_ENCRYPTION_KEY` | 32 random bytes, base64 (`openssl rand -base64 32`). Encrypts saved assessments. Losing it makes saved data unreadable, so back it up outside Vercel. |
| `DATA_ENCRYPTION_KEY_PREVIOUS` | Optional. Put the old key here when rotating; records re-encrypt on next save. |
| `CARDIOSENSE_USERS` | Bootstrap accounts, JSON: `{"you@example.org": {"hash": "scrypt$...", "role": "admin", "name": "You"}}`. Use it to create the first admin, then create everyone else from the dashboard. |
| `GITHUB_TOKEN`, `GITHUB_REPO` | Read access to the repository whose latest Release holds the installers (see `api/_lib/releases.js`). |

## 3. First admin

```bash
node scripts/add-user.js you@example.org "a long passphrase" admin "Your Name"
```

Put the printed JSON in `CARDIOSENSE_USERS`, deploy, sign in, then use **Dashboard > People** to create accounts.
New accounts get a temporary password shown once and must change it at first sign-in.

## 4. Tests

```bash
npm run test:api     # node API tests (in-memory database)
python -m pytest     # repository suite
python evaluate.py   # regenerates artifacts/validation.json
```

## Privacy notes

- Saved assessments hold the 13 model inputs, the risk and a short reference. The API rejects anything else.
- Records are AES-256-GCM encrypted and bound to owner and record id before they reach the database.
- Sessions are server-side and revocable. Emails and IPs appear in the database only as keyed hashes (accounts keep the email inside the user record).
- Before real patient data: add a privacy notice and retention rule, and follow India's DPDP Act or your local law.
