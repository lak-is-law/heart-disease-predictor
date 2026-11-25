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

## Sign in with Google, Microsoft, X and ChatGPT

Email and password sign-up works with no extra setup. Each social button switches on when its credentials are set in the Vercel project. Buttons without credentials are shown dimmed.

Set `SITE_URL` to `https://cardiosense.lakshya.uk`. In each provider's console, register this redirect URL, then add the variables.

| Provider | Redirect URL | Variables |
| --- | --- | --- |
| Google | `https://cardiosense.lakshya.uk/api/oauth/google/callback` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (Google Cloud Console, OAuth client, Web application) |
| Microsoft | `https://cardiosense.lakshya.uk/api/oauth/microsoft/callback` | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` (Entra ID app registration, Web platform, multi-tenant and personal accounts) |
| X | `https://cardiosense.lakshya.uk/api/oauth/x/callback` | `X_CLIENT_ID`, `X_CLIENT_SECRET` (X developer portal, OAuth 2.0, scopes `users.read tweet.read`) |
| ChatGPT | `https://cardiosense.lakshya.uk/api/oauth/openai/callback` | `OPENAI_OAUTH_CLIENT_ID`, `OPENAI_OAUTH_CLIENT_SECRET`, `OPENAI_OAUTH_AUTH_URL`, `OPENAI_OAUTH_TOKEN_URL`, `OPENAI_OAUTH_USERINFO_URL` |

Notes:

- **Continue with ChatGPT (Sign in with ChatGPT)**: OpenAI offers an official login partner program via [Sign in with ChatGPT](https://developers.openai.com/siwc) ([Quickstart](https://developers.openai.com/siwc/quickstart)). Request a Client ID and register:
  - **Website URL**: `https://cardiosense.lakshya.uk`
  - **OAuth Callback URL**: `https://cardiosense.lakshya.uk/api/oauth/openai/callback`
  Once OpenAI provisions your client credentials and OIDC endpoints, set `OPENAI_OAUTH_CLIENT_ID`, `OPENAI_OAUTH_CLIENT_SECRET`, `OPENAI_OAUTH_AUTH_URL`, `OPENAI_OAUTH_TOKEN_URL`, and `OPENAI_OAUTH_USERINFO_URL`.
- X does not return an email address. Those accounts get a placeholder address and are never linked to an existing email account.
- A social sign-in is linked to an existing account only when the provider confirms the email address (Google). Otherwise the visitor is asked to sign in with their password.
- Set `CARDIOSENSE_SIGNUP=closed` to turn off open sign-up and keep admin-created accounts only.
