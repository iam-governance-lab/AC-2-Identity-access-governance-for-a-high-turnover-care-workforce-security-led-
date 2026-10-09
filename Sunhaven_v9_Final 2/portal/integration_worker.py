"""Isolated, read-only adapters to the preserved original project."""
from pathlib import Path
import csv, json, sys, tempfile, shutil
ROOT=Path(__file__).resolve().parents[1]/'original'

def main(kind,payload):
    if kind=='smfaa':
        src=ROOT.parent/'team_lab/services/Sunhaven MFA Fatigue Attack Analyzer'
        sys.path.insert(0,str(src/'src'))
        from detector import build_event, load_rules, detect_findings, load_normalized_csv
        events=load_normalized_csv(src/'data/demo-events.csv') if payload['mode']=='demo' else [build_event(row) for row in payload['rows']]
        findings=detect_findings(sorted(events,key=lambda e:e.timestamp),load_rules(src/'config/detection-rules.json'))
        return {'mode':payload['mode'],'engine':'Full teammate SMFAA detector','events_analyzed':len(events),'findings':findings,'decision_rule':'Investigation findings only. Human approval required; no access is changed.'}
    if kind=='sitas':
        src=ROOT/'sunhaven-sitas-threat-simulator'
        sys.path.insert(0,str(src/'src'))
        import sitas
        from sunhaven_adapter import build_sunhaven_snapshot,build_integrated_leaver_comparison
        core=sitas.load_core_files()
        if core is None:raise ValueError('SITAS configuration is incomplete.')
        original=build_sunhaven_snapshot(ROOT)
        with tempfile.TemporaryDirectory(prefix='sunhaven-sitas-') as tmp:
            target=Path(tmp);(target/'data').mkdir();shutil.copytree(ROOT/'config',target/'config')
            fields=['employeeId','displayName','mailAlias','jobRole','facility','status','startDate','endDate']
            with (target/'data/workforce.csv').open('w',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
                for e in payload['workers']:
                    writer.writerow(dict(zip(fields,[e['employee_id'],e['name'],e['email'].split('@')[0],e['approved_role'],e['facility'],e['status'],e['start_date'],e['end_date'] or ''])))
            current=build_sunhaven_snapshot(target)
            try:leaver=build_integrated_leaver_comparison(target,core[1],core[2])
            except ValueError as exc:leaver={'message':str(exc)}
        return {'mode':'Original SITAS engine; synthetic portal snapshot; no Graph calls','scenarios':sitas.compare_all(core),'original_workforce':original['workforce'],'portal_workforce':current['workforce'],'mapping_findings':current['findings'],'portal_leaver_comparison':leaver}
    if kind=='saif':
        src=ROOT/'sunhaven-saif-agency-identity-federation'
        sys.path.insert(0,str(src/'src'))
        from saif_agency_validation import validate_worker
        from saif_b2b_invitation import prepare_invitation
        agencies=json.loads((src/'config/approved-agencies.json').read_text())['agencies']
        result=validate_worker(payload,agencies)
        return {'mode':'Original SAIF validation and invitation preview only; nothing sent','result':result,'preview':prepare_invitation(payload,'https://sunhaven.example/agency') if result=='APPROVED' else None}
    raise ValueError('Unknown adapter')

if __name__=='__main__':
    try:print(json.dumps(main(sys.argv[1],json.load(sys.stdin))))
    except Exception as exc:print(json.dumps({'error':str(exc)}));sys.exit(1)
