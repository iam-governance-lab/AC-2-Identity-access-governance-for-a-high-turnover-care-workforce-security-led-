"""Explainable MFA sequence detector on controlled, sanitised events."""
from collections import defaultdict
from datetime import datetime,timezone,timedelta

OUTCOMES={'denied','success','challenge','timeout','unknown_failure'}
def analyze(events,window_minutes=5,denial_threshold=3,prompt_threshold=5):
    if not (1<=window_minutes<=60 and 2<=denial_threshold<=20 and 3<=prompt_threshold<=50):raise ValueError('Invalid detector thresholds')
    parsed=[];seen=set()
    for e in events:
        if not isinstance(e,dict):raise ValueError('Each event must be an object')
        eid=e.get('event_id');who=e.get('actor_id');outcome=e.get('outcome');raw=e.get('timestamp_utc')
        if not isinstance(eid,str) or not eid or len(eid)>100 or not isinstance(who,str) or not who or len(who)>100 or outcome not in OUTCOMES:
            raise ValueError('Invalid event ID, actor or MFA outcome')
        if eid in seen:continue
        seen.add(eid)
        try:stamp=datetime.fromisoformat(raw.replace('Z','+00:00'))
        except (ValueError,AttributeError):raise ValueError('Invalid event timestamp')
        if stamp.tzinfo is None:raise ValueError('Timestamp must contain a UTC offset')
        parsed.append((stamp.astimezone(timezone.utc),eid,who,outcome))
    parsed.sort();grouped=defaultdict(list)
    for e in parsed:grouped[e[2]].append(e)
    findings=[]
    for who,rows in grouped.items():
        emitted=set()
        for index,current in enumerate(rows):
            bucket=[r for r in rows[:index+1] if current[0]-r[0]<=timedelta(minutes=window_minutes)]
            denials=[r for r in bucket if r[3]=='denied']
            prompts=[r for r in bucket if r[3] in ('challenge','denied','timeout')]
            rules=[]
            if len(denials)>=denial_threshold:rules.append(('MFA_REPEATED_DENIAL','High',denials,'Repeated user denials'))
            if len(prompts)>=prompt_threshold:rules.append(('MFA_PROMPT_BURST','High',prompts,'Burst of MFA prompts'))
            if current[3]=='success' and len(denials)>=denial_threshold:rules.append(('MFA_DENIAL_TO_SUCCESS','Critical',denials+[current],'Denials followed by success'))
            for rule,severity,matched,explanation in rules:
                if rule in emitted:continue
                emitted.add(rule)
                findings.append({'rule_id':rule,'severity':severity,'actor_id':who,'timestamp_utc':current[0].isoformat().replace('+00:00','Z'),
                  'event_ids':[r[1] for r in matched], 'explanation':f'{explanation}: {len(matched)} related events within {window_minutes} minutes.'})
    return findings
