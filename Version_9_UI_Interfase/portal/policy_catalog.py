"""Versioned, inspectable control catalogue for the synthetic Sunhaven lab."""
POLICY_VERSION='1.0'
CONTROLS=[
 ('P01','Identity lifecycle','Use an approved workforce record and dry run before Joiner, Mover or Leaver.','JML owner','JOINER/MOVER/LEAVER','tests/test_core.py'),
 ('P02','Two-person change','A different authorised person approves an access change; an operator executes a current approved request.','Manager / IAMOperator','APPROVED_MOVER_EXECUTED','tests/test_governance.py'),
 ('P03','Least privilege','Check role, facility and active resident assignment on the server.','App owner','ACCESS_ALLOWED / ACCESS_DENIED','tests/test_web.py'),
 ('P04','Agency time limit','Every agency record has a sponsor and end date; expired access is blocked and local expiry run disables it.','IAMOperator','AGENCY_EXPIRY_ENFORCED','tests/test_automation.py'),
 ('P05','Leaver and session denial','Revoke local sessions, remove role and assignments, and block leavers.','IAMOperator','LEAVER','tests/test_core.py'),
 ('P06','Periodic review','Review active worker access every 90 days and record a reason and remediation.','Manager / Auditor','ACCESS_REVIEW','tests/test_web.py'),
 ('P07','Audit integrity','Record actor, action, result, UTC time and correlation; verify a signed local ledger checkpoint.','IAMOperator / Auditor','Security assurance','tests/test_security_workstream.py'),
 ('P08','Authentication','Enforce a 15-minute absolute local session. Production requires approved Entra login and externally configured MFA.','Tenant owner','LOGIN_ENTRA / LOGIN_LOCAL_DEMO','tests/test_web.py'),
 ('P09','Secret handling','Keep passwords and signing keys out of reports, logs and shared source bundles.','Operator','Audit redaction / key sidecar','tests/test_core.py'),
 ('P10','Assurance and response','Scan policy violations, assign remediation ownership and keep evidence until closure.','Manager / Auditor','C01-C08 / tasks','tests/test_governance.py'),
]
RISKS=[
 ('R01','Former worker retains access','Critical','P01,P05','Leaver route plus blocked-user check','Actual cloud disable still unverified'),
 ('R02','Agency contract expires','High','P04','Daily reviewed local expiry run','External directory remains simulated'),
 ('R03','Privilege accumulation','High','P02,P03','Approved mover replaces role and clears assignments','Manager scope is organisation-wide'),
 ('R04','Shared workstation reuse','High','P05,P08','Absolute local session expiry and revoke','Device trust and unattended session proof missing'),
 ('R05','Audit record alteration','High','P07,P09','HMAC ledger plus separate signed checkpoint','Same-host key compromise remains possible'),
 ('R06','MFA prompt fatigue','High','P08,P10','Controlled event detector','No live Entra export ingested'),
 ('R07','Overdue access recertification','Medium','P06,P10','90-day finding plus reminder','Reviews remain human-driven'),
]
