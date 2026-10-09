# Sunhaven Care IAM 4.0 — workspace guide

This supplement covers the version 4 additions. The included Operating and Technical Guide DOCX describes the version 3 foundation: joiners, movers, leavers, approvals, assignments, remediation, reviews, authentication and deployment configuration. Read both documents together. All supplied people, residents and notes are fictional.

## Start and explore

Extract the complete ZIP. In `sunhaven_care_iam`, run `python run.py` (or `python3 run.py`) and open http://127.0.0.1:8000. Windows users can double-click `start_windows.bat`. Choose Ivy Chen for operator functions, Daniel Lee for manager functions, Omar for read-only audit work, or Mia Patel for a restricted worker view. Demo login deliberately has no password and must remain local.

## New features

| Feature | Operation | Access and behaviour |
|---|---|---|
| Facility chart | Dashboard → Who has access? → choose a facility | Managers, auditors and operators see active workers grouped by role. Counts are read from SQLite on page load. Switching facilities filters that snapshot. Refresh to fetch changes. |
| Clickable statistics | Select a dashboard statistic | Active/leaver counts open filtered reports; agency workers opens the directory; findings opens compliance. |
| Theme | Select the half-circle button in the header | Light/dark choice is stored in this browser. First use follows the operating system preference where available. |
| Global search | Type in the header or press `/`, then Enter | Search requires at least two characters. Governance roles can search worker names, IDs, emails, note text, task titles and requests. Workers can search their own requests only. Results have per-category limits of 20 or 30. |
| Notifications | Open Notifications or the circular header icon | Pending requests, agency contracts due within 14 days or expired, and reviews older than 90 days. Workers see only their own pending requests. Mark read is personal; it does not resolve the underlying issue. |
| Approval history | Access requests → View approval history | Displays submission, decision and implemented change with actors and times. Owners and governance roles may view a request. Older records may have no decision timestamp. |
| Onboarding | Select a worker → Open checklist | Managers/operators can tick four steps, use Select all steps, enter evidence and Save checklist. Unchecking a saved step reopens it. Auditors can view. Checklist completion does not grant access. |
| PDF reports | Reports → select facility/status → Apply filters → Download PDF | Governance roles only. Exports aggregate workforce counts by role and status for the selected filters; excludes names and note text. Export is audited. |

## Suggested demonstration

1. Sign in as Ivy and filter the role chart by North Wing.
2. Switch to dark mode, then press `/` and search for Sarah.
3. Open Sarah's profile and inspect the existing notes and role information.
4. Open Onboarding, choose Sarah, complete two steps and save with evidence. Reload to show persistence.
5. Open Notifications and mark one item read. Its underlying issue remains available.
6. Open an access request's history. Use the existing approval/execution workflow to show additional history entries.
7. Download an Active / North Wing report.
8. Sign in as Mia. Confirm that governance pages are denied and search/notifications show only her permitted requests.

## Technical design

`experience.py` adds the new route handlers through the existing AppHandler mixin structure. Both the local HTTP server and production WSGI adapter use the same handlers. `ui.py` provides shared navigation, theme controls and search. `static/workspace.css` layers version 4 styling over the existing stylesheet; `theme.js` applies the preferred theme early; `app.js` handles chart selection, keyboard search and checklist selection. No new package installation is needed for local demo mode.

`database.init_db()` creates two additive tables without deleting existing rows:

- `notification_reads`: composite primary key employee ID + reminder key; stores the read timestamp.
- `onboarding_steps`: composite primary key employee ID + step number; stores completion, evidence, actor and timestamp.

Onboarding writes use `BEGIN IMMEDIATE`; step updates and the audit event commit together. Evidence must be 10–2,000 characters. Step rows retain the latest evidence for changed steps; the audit log records each submitted update. Approval history reads the existing request and execution snapshot tables. Notification rules run on page requests; there is no background scheduler, email or push delivery.

Search uses bound SQL parameters, literal escaping of LIKE wildcards, and HTML escaping. Roles are checked on the server; hidden navigation is not the security boundary. Existing CSRF protection applies to onboarding and notification read forms. Report filters use configured enum values. PDF downloads set `Cache-Control: no-store` and emit an audit event.

The report generator emits a simple paginated PDF 1.4 using standard Helvetica. Its input is fixed labels, timestamps, configured ASCII role/facility names and aggregate counts. It is not a general Unicode rich-text renderer. Reports are generated on demand and are not stored on the server.

## Upgrade, backup and maintenance

Back up the existing SQLite database with the supplied `manage.py backup` command (see `python manage.py --help`). Stop the old process, replace application code while preserving your database and environment configuration, then start version 4. Startup creates the additive tables automatically. Do not replace an existing populated database with the demo database from this ZIP. A rollback to v3 can retain the added tables, but v3 will not display their contents.

Run `python -m unittest discover -s tests -v` from the project folder. Version 4 has 38 passing automated tests. Browser preferences are per-device; clearing site data resets the theme. If styling appears old after an upgrade, perform a hard refresh.

## Verified scope and remaining limits

The local routes, role restrictions, persistence, CSRF behaviours and PDF responses were exercised through the WSGI test adapter. JavaScript syntax was checked. A sample PDF was rendered for layout inspection. Full interactive browser/mobile visual testing was unavailable in this environment, so CSS and JavaScript interactions still need acceptance checks on target browsers.

This is an enhanced runnable prototype with deployment configuration. Microsoft Graph provisioning remains simulated and live directory mode is intentionally blocked. Entra sign-in, Docker/HTTPS hosting, restore drills, load testing and operational monitoring have not been validated in a live deployment. Managers have organisation-wide governance scope. Onboarding is evidence tracking, not a mandatory provisioning gate. The application has not been certified as production-ready or deployed by this update.
