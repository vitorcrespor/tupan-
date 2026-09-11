# Supabase Auth v2 validation and cutover

Supabase is adopted as a managed platform component, not as a desktop data
client. The desktop continues to call the Tupan FastAPI API only. FastAPI owns
tenant resolution, authorization, analytics orchestration, and opaque session
cookies; Supabase Auth owns credential creation and password verification.

## What moves to Supabase

- **Auth:** credentials and password verification through Supabase Auth.
- **PostgreSQL/PostGIS/pgvector:** the existing application schema can run on
  the Supabase PostgreSQL instance through the restricted `DATABASE_API_URL`
  connection role.

The following stay in the backend: RLS tenant context, organization membership
authorization, AVM/XGBoost, H3/heatmap processing, jobs, AI orchestration, and
the opaque server-side `auth_sessions` table. The browser must never receive a
database connection, service-role key, or a direct table API credential.

## Stage the v2 adapter

1. Create a Supabase project with email/password sign-in enabled.
2. Put only these values in the backend `.env`:

   ```dotenv
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_ANON_KEY=<publishable-anon-key>
   DATABASE_API_URL=<restricted Supabase Postgres application role URL>
   ```

3. Apply migrations `001` through `008` to the Supabase database. Migration
   `008_supabase_auth_v2.sql` explicitly requires the managed `auth.users`
   table and adds `cloud_users.supabase_user_id` without deleting any account.
4. Start FastAPI and check the isolated dependency boundary:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8000/api/v2/ready
   ```

   It must return both `database` and `supabase_auth` as `ok`.
5. Exercise the v2 endpoints with a new test account:

   ```text
   POST /api/v2/auth/register
   POST /api/v2/auth/login
   GET  /api/v2/auth/session
   POST /api/v2/auth/logout
   ```

   Confirm the response is the same user shape as v1, has no provider token,
   and sets only an HttpOnly `tupan_session_supabase_v2` cookie.

## Existing-account migration

The first successful v2 login handles two verified cases:

1. If the account already exists in Supabase, Tupan links its authorized local
   profile only after the user has passed the Supabase password grant.
2. If an authorized Tupan account has only the old `scrypt` hash, its supplied
   password is verified once, a Supabase identity is created, and the identity is
   linked. The hash remains only through parallel v1/v2 validation so v1 login
   continues to work.

There is no bulk password-hash import and no silent reassignment by email.

## Cutover and legacy removal gate

Do **not** remove the v1 service or old password column merely because mocked
tests pass. First record all of the following against a real non-production
Supabase project:

- `GET /api/v2/ready` is ready;
- v2 registration, login, session, and logout succeed;
- duplicate registration returns the intended conflict response;
- invalid credentials return `401 authentication_required`;
- a legacy account links to its Supabase identity while its v1 login remains usable;
- a cross-tenant request remains blocked by the existing RLS tests;
- the retained v1 HTTP contract tests still pass.

After that evidence exists, promote the Supabase implementation behind the
current `/api/v1/auth/*` routes so the desktop does not need a URL migration,
then remove the old custom-password implementation and finally drop the
unused `password_hash` column only after every active profile has a
`supabase_user_id`. Keep the v2 path only for the verification period; it is
not a permanent second API.
