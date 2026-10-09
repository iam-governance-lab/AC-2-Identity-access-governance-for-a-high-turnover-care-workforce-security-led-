"""Reproducible retrieval fitting and workflow routing evaluation.
This fits TF-IDF weights over curated examples. It does not fine-tune an LLM.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'portal'))
import help_assistant as h
CASES=[
('I need to add a permanent staff member','joiner'),
('Where can I register an agency replacement?','sponsor'),
('I want to change a worker role and facility','transfer'),
('A worker has left and must be offboarded','termination'),
('How can a manager reject a role request?','requests'),
('Where can I request an application entitlement?','apps'),
('How do I arrange an on duty shift?','shifts'),
('Compare delivered app permissions with approvals','connector'),
('The provisioning retry has failed again','retry'),
('Where do I renew safeguarding evidence?','qualifications'),
('A nurse needs urgent emergency resident access','emergency'),
('How do I request temporary site cover?','cover'),
('Where are quarterly certification campaigns?','campaigns'),
('How can I mark inbox reminders as read?','inbox'),
('Can I bookmark my directory filters?','views'),
('I need to search a previous handover note','notes'),
('Who changed the account? I need audit evidence','audit'),
('Where can I download a CSV report?','reports'),
('How do I run automatic expiry jobs?','automation'),
('How do I stage a bulk roster CSV?','roster'),
('How do I check the owner of a service account?','services'),
('Explain unusual access risk signals','insights'),
('Where can I inspect a policy violation?','policies'),
('How do I sign in through SSO?','login'),
('The form says request expired error','errors'),
('How do I restore my database backup?','backup'),
('How can I open the tablet menu?','navigation'),
('What is the weather in Sydney?',''),
('Order me a takeaway pizza',''),
('Where can I see account recertification?','reviews'),
]
topics,idf,vectors,norms=h.train();results=[]
for q,expected in CASES:
    r=h.answer(q,{'IAMOperator'});results.append({'question':q,'expected':expected,'actual':r['topic'],'pass':r['topic']==expected})
report={'model':'TF-IDF workflow retrieval, no generative model','knowledge_topics':len(topics),'training_examples':sum(len(t['examples']) for t in topics),'vocabulary_size':len(idf),'corpus_sha256':hashlib.sha256((ROOT/'portal/help_topics.json').read_bytes()).hexdigest(),'evaluation':'Curated routing regression examples, refined during development; not a held-out or general intelligence benchmark','passed':sum(r['pass'] for r in results),'total':len(results),'results':results}
(ROOT/'evidence/final9/assistant-evaluation.json').write_text(json.dumps(report,indent=2))
(ROOT/'portal/help_model.json').write_text(json.dumps({'kind':'tfidf','corpus_sha256':report['corpus_sha256'],'idf':idf,'vectors':vectors,'norms':norms,'topic_ids':[t['id'] for t in topics]},indent=2))
print(json.dumps(report,indent=2));raise SystemExit(0 if all(r['pass'] for r in results) else 1)
