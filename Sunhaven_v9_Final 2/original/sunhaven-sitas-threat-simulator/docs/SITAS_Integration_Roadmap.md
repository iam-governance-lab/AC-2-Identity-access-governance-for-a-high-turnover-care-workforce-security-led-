# SITAS Integration Roadmap

## Completed milestone 1 – Standalone analysis completion

Implemented:

- automatic control OFF/ON comparison;
- structured analysis results;
- JSON result export;
- CSV scenario summary;
- static HTML threat report;
- regression tests for comparison/reporting.

## Completed milestone 2 – Sunhaven project integration

Implemented a read-only adapter that consumes the actual group-project structure:

- `data/workforce.csv`
- `config/route-role-map.csv`
- `config/app-role-ids.json`
- `config/group-object-ids.json`
- presence of JML/state-export/application artefacts
- optional sanitised worker-state CSV
- optional sanitised leaver-result JSON

The adapter now provides:

- automatic parent-repository discovery when SITAS is stored inside Sunhaven;
- explicit `--root` support for standalone development;
- validated workforce/configuration loading;
- Sunhaven-derived former-worker analysis;
- RBAC allow/deny matrix from the current project configuration;
- control-to-project boundary mapping;
- integrated JSON/CSV/HTML reporting;
- 16 integration-specific automated tests.

Current full suite:

```text
66 passed
```

## Remaining finalisation work

The remaining SITAS work is assessment/evidence polish rather than another core implementation phase:

1. refresh architecture/flow diagrams to show `sunhaven_adapter.py`;
2. capture final `sunhaven-status`, `sunhaven-leaver`, `sunhaven-report` and pytest evidence;
3. verify the clean SITAS folder inside the downloaded main project;
4. upload the clean SITAS folder to the main GitHub repository;
5. keep the standalone SITAS repository as individual development-history evidence;
6. rehearse the final demonstration and explanation of ownership boundaries.
