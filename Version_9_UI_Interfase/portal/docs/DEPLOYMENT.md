# Deployment guide — version 2

## Local demonstration (ready to run)

Use Python 3.10+ and `python run.py`, then open http://127.0.0.1:8000.
The application seeds synthetic data only when its database is empty and
SUNHAVEN_SEED_DEMO=1. The supplied database already contains the expanded demo.
The Docker image excludes local databases, secrets and compiled Python files.

With Docker installed, `docker compose up --build -d` creates a local demo,
with persistent `demo-data` volume and port 8000 bound to 127.0.0.1 only.
`docker compose down` stops it without deleting the volume. Do not add `-v`
unless you intentionally want to delete its database.

## Controlled hosted demonstration with Entra

This configuration is prepared but requires your own infrastructure and live
authentication validation. Directory lifecycle changes remain simulated.

1. Supply a Linux host with Docker Compose and persistent disk. Point your DNS
   hostname at it. Allow inbound TCP 80/443. Do not expose port 8000.
2. Register a single-tenant confidential web app in Microsoft Entra. Configure
   `https://YOUR-HOST/auth/callback` as its Web redirect URI. Enforce required
   user assignment and the organisation's MFA policy in Entra.
3. Copy `.env.production.example` to `.env.production`. Fill the tenant ID,
   client ID, client secret and HTTPS redirect. Generate the app secret with
   `python -c "import secrets; print(secrets.token_urlsafe(48))"` and store it
   securely. Never commit populated environment files.
4. Set `SUNHAVEN_DOMAIN` in the shell to the DNS hostname. It is consumed by
   Docker Compose for the proxy (not automatically from `.env.production`).
5. Run `docker compose -f compose.production.yaml up --build -d`.
   Caddy supplies TLS; the application is reachable only on the Compose network.
   Production mode requires Entra, a 32+ character secret, HTTPS redirect and
   no demo seeding. The production volume is separate from demo data.
6. Provision the first operator using the immutable **user object ID**, not the
   application object ID. Replace every example below with your actual values:

```sh
docker compose -f compose.production.yaml exec app python manage.py bootstrap \
  --employee-id ADMIN001 --name "Approved Operator" \
  --email operator@example.org --object-id USER-OBJECT-GUID
```

7. Sign in and verify correct and incorrect user access, MFA policy, session
   expiry, logout, HTTPS cookies and startup after container restart. Test all
   role boundaries with separate tenant test identities before inviting others.

Bootstrap only accepts an empty workforce database. New mock Joiners receive
mock object IDs and cannot use real Entra sign-in until an administrator builds
and validates an approved identity-mapping/provisioning process. Do not treat
this release as a live directory provisioning system.

## Database backup and restore

Use `python manage.py backup backups/unique-name.db` for a consistent SQLite
backup, including committed WAL content. A pre-existing destination is refused.
For Docker use `docker compose ... exec app python manage.py backup /data/backup.db`
and copy that file to secured off-host storage. Keep backups outside the live volume.

Restore procedure: stop the app, retain an independent copy of the current database,
restore a verified backup as `/data/sunhaven.db`, remove obsolete WAL/SHM sidecars
only while the app is stopped, ensure UID 10001 can read/write the file and directory,
then restart. Check `/health`, sign-in and record counts. Never copy only a live
WAL-mode database file; use the backup command. Test restore before relying on it.

## Release constraints

- Docker executable was unavailable in the build environment; container build,
  certificate issuance and Compose deployment require verification on your host.
- Real Entra sign-in was not tested with a tenant. No credentials are bundled.
- Real Graph writes fail closed at startup, since local rollback cannot undo
  partial remote changes. The old Graph adapter remains as reference code.
- One instance only. Use a database and deployment migration plan before scaling.
- Add monitoring, rate limits at the gateway, backup scheduling, dependency scans,
  retention rules and independent security review before any real operational use.
- The UI remains a synthetic-data demonstration even with Entra sign-in.
