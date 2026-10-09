"""Locally trained TF-IDF retrieval over curated workflow examples. No LLM calls.
Only static help is indexed; identity records, notes and transcripts are never indexed.
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json,math,re,hashlib
from difflib import get_close_matches
STOP=set('a an the i me my we you your it is are to for of and in on do how can please with want need would like tell what where'.split())
SYN={'onboarding':'onboard','onboarded':'onboard','employees':'employee','workers':'worker','permissions':'permission','requests':'request','notifications':'notification','qualifications':'qualification','fired':'terminate','leaving':'terminate','leaves':'terminate','offboard':'offboarding','certificates':'qualification','credentials':'qualification','approvals':'approval','approving':'approve','accounts':'account','shifts':'shift','erro':'error','privileges':'privileged','bot':'assistant','chatbot':'assistant'}
def tokens(text):
    return [SYN.get(x,x) for x in re.findall(r'[a-z0-9]+',str(text).lower()) if x not in STOP]

@lru_cache(maxsize=1)
def train():
    topics=json.loads((Path(__file__).with_name('help_topics.json')).read_text())
    model=Path(__file__).with_name('help_model.json')
    if model.exists():
        try:
            saved=json.loads(model.read_text())
            digest=hashlib.sha256(Path(__file__).with_name('help_topics.json').read_bytes()).hexdigest()
            if saved['corpus_sha256']==digest and saved['topic_ids']==[t['id'] for t in topics]:return topics,saved['idf'],saved['vectors'],saved['norms']
        except (ValueError,KeyError,TypeError):pass
    docs=[Counter(tokens(t['title']+' '+' '.join(t['examples']))) for t in topics]
    df=Counter(k for d in docs for k in d);idf={k:math.log((1+len(docs))/(1+n))+1 for k,n in df.items()}
    vectors=[{k:(1+math.log(v))*idf[k] for k,v in d.items()} for d in docs]
    norms=[math.sqrt(sum(v*v for v in d.values())) for d in vectors]
    return topics,idf,vectors,norms

def permitted(topic,roles):return not topic['roles'] or bool(set(topic['roles'])&set(roles))
def topics_for(roles):return [t for t in train()[0] if permitted(t,roles)]
def topic_for_path(path,roles):
    matches=[t for t in topics_for(roles) if t['path']!='/' and path==t['path']]
    return matches[0]['id'] if matches else 'start'

def answer(question,roles,previous='',context=''):
    question=str(question or '').strip()
    if not 1<=len(question)<=1000:raise ValueError('Ask a question of 1 to 1000 characters.')
    topics,idf,vecs,norms=train();byid={t['id']:t for t in topics};low=question.lower().strip(' ?.!');score=0.;topic=None
    follow=low in {'how','how do i do it','show the steps','steps','next','continue','where','where do i find it','what do i need','why','explain more','tell me more'} or bool(re.fullmatch(r'step [1-9]',low))
    if follow and previous in byid:topic=byid[previous];score=1
    elif low in {'this page','help on this page','explain this page'} and context in byid:topic=byid[context];score=1
    elif low in {'hello','hi','hey','help','start','thanks','thank you'}:topic=byid['start'];score=1
    else:
        words=tokens(question)
        words=[(get_close_matches(w,idf,n=1,cutoff=.84) or [w])[0] if w not in idf and len(w)>5 else w for w in words]
        q=Counter(words);qv={k:(1+math.log(v))*idf[k] for k,v in q.items() if k in idf};qn=math.sqrt(sum(v*v for v in qv.values())) or 1
        ranked=[]
        for t,v,n in zip(topics,vecs,norms):
            cosine=sum(value*v.get(k,0) for k,value in qv.items())/(qn*n or 1)
            overlap=len(set(q)&set(v))
            if any(example.lower()==low for example in t['examples']):cosine=1
            ranked.append((cosine,overlap,t))
        ranked.sort(key=lambda x:(x[0],x[1]),reverse=True);score,overlap,topic=ranked[0]
        if score<.14 or not overlap:topic=None
    base={'mode':'Local trained help retrieval - no generative model or external data','suggestions':['How do I request app access?','Help on this page','How do I recover from an error?']}
    if topic is None:return {**base,'topic':'','title':'Let’s narrow that down','text':'I do not have a reliable documented answer for that yet. Tell me the feature or task, such as onboarding, an access request, a shift, or a failed connector job.','steps':[],'prerequisites':'I only answer from the Sunhaven help library. No action was performed.','link':'/help','confidence':0}
    if not permitted(topic,roles):return {**base,'topic':'','title':'This workflow needs another role','text':topic['title']+' needs an authorized '+', '.join(topic['roles'])+'. Ask your manager or IAM operator to help.','steps':[],'prerequisites':'Your permissions have not changed. I cannot bypass approval or role checks.','link':'/help','confidence':round(score,2)}
    text=topic['summary'];steps=topic['steps']
    if low=='what do i need':text=topic['prerequisites'];steps=[]
    elif re.fullmatch(r'step [1-9]',low):
        n=int(low[-1]);steps=steps[n-1:n];text='Here is that step. '+topic['summary'] if steps else 'That workflow has fewer steps. Ask me to show the steps again.'
    return {**base,'topic':topic['id'],'title':topic['title'],'text':text,'steps':steps,'prerequisites':topic['prerequisites'],'link':topic['path'],'confidence':round(min(score,1),2),'suggestions':['Show the steps','What do I need?','Where do I find it?']}
