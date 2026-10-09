document.addEventListener('DOMContentLoaded',()=>{
  const dialog=document.querySelector('#assistantDialog');if(!dialog)return;
  const form=document.querySelector('#assistantForm'),input=document.querySelector('#assistantQuestion'),log=document.querySelector('#assistantMessages'),status=document.querySelector('#assistantStatus'),suggestions=document.querySelector('#assistantSuggestions'),launcher=document.querySelector('#assistantLauncher');
  let previous='',busy=false,controller=null,generation=0,history=[];
  function bubble(text,who){const item=document.createElement('article');item.className='chat-message '+who;const label=document.createElement('strong');label.textContent=who==='user'?'You':'Sunhaven';const p=document.createElement('p');p.textContent=text;item.append(label,p);log.append(item);while(log.children.length>12)log.firstElementChild.remove();return item;}
  function welcome(){bubble('Hello! Ask about a task, your own access, or a workflow. I can guide you step by step. An administrator can also enable AI assistance for live, role-filtered summaries.','assistant');}
  welcome();
  launcher.addEventListener('click',()=>{if(typeof dialog.showModal!=='function'){location.href='/help';return;}dialog.showModal();input.focus();});
  dialog.addEventListener('close',()=>launcher.focus());
  async function ask(question){
    if(busy||!question.trim())return;busy=true;const mine=generation;controller=new AbortController();const requestController=controller;const timeout=setTimeout(()=>requestController.abort(),20000);
    const button=form.querySelector('button[type=submit]');button.disabled=true;form.setAttribute('aria-busy','true');status.textContent='Checking Sunhaven guidance…';bubble(question,'user');input.value='';
    try{
      const csrf=form.querySelector('[name=_csrf]')?.value||'';
      const response=await fetch('/assistant/ask',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'},body:new URLSearchParams({question,previous,context:dialog.dataset.context,history:JSON.stringify(history.slice(-4)),_csrf:csrf}),signal:requestController.signal});
      if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('Your session may have expired. Reload or sign in again.');
      const data=await response.json();if(!response.ok)throw new Error(data.error?.message||'Help is temporarily unavailable. Browse the Help centre or try again.');
      if(mine!==generation)return;
      if(!data||typeof data.text!=='string'||typeof data.title!=='string'||!Array.isArray(data.suggestions)||!data.suggestions.every(x=>typeof x==='string')||(data.steps&&!Array.isArray(data.steps)))throw new Error('Invalid help response. Try again or open Help centre.');
      previous=data.topic;history.push({q:question.slice(0,400),a:data.text.slice(0,500)});history=history.slice(-4);const item=bubble(data.text,'assistant');const title=document.createElement('h3');title.textContent=data.title;item.prepend(title);
      if(data.steps?.length){const list=document.createElement('ol');data.steps.forEach(step=>{const li=document.createElement('li');li.textContent=step;list.append(li)});item.append(list);}
      const note=document.createElement('p');note.className='muted';note.textContent=data.prerequisites;item.append(note);
      if(data.link?.startsWith('/')&&!data.link.startsWith('//')){const link=document.createElement('a');link.className='btn btn-secondary';link.href=data.link;link.textContent='Open '+(data.link==='/help'?'Help centre':data.title);item.append(link);}
      suggestions.replaceChildren(...data.suggestions.map(q=>{const b=document.createElement('button');b.type='button';b.className='btn btn-secondary';b.dataset.question=q;b.textContent=q;return b;}));status.textContent=(data.mode||'Sunhaven guidance')+'. No action performed.';
    }catch(error){if(mine===generation){bubble(error.name==='AbortError'?'The request timed out. Try again, or use the Help centre.':error.message,'assistant');status.textContent='Could not retrieve help. Your task has not been submitted.';}}
    finally{clearTimeout(timeout);if(mine===generation){busy=false;button.disabled=false;form.removeAttribute('aria-busy');input.focus();log.scrollTop=log.scrollHeight;}}
  }
  form.addEventListener('submit',e=>{e.preventDefault();ask(input.value)});
  suggestions.addEventListener('click',e=>{const b=e.target.closest('[data-question]');if(b)ask(b.dataset.question)});
  document.querySelector('#assistantClear').addEventListener('click',()=>{generation++;controller?.abort();busy=false;previous='';history=[];log.replaceChildren();welcome();status.textContent='Conversation cleared. Nothing was saved.';form.removeAttribute('aria-busy');form.querySelector('button[type=submit]').disabled=false;input.value='';input.focus();});
});
