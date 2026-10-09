document.addEventListener('DOMContentLoaded', () => {
  const sidebar=document.querySelector('.sidebar'), main=document.querySelector('main'), toggle=document.querySelector('.menu-toggle'), backdrop=document.querySelector('.nav-backdrop');
  const small=matchMedia('(max-width: 1180px)');
  function drawer(open,restore=true) {
    if(!sidebar)return;
    document.body.classList.toggle('nav-open',open);
    sidebar.inert=small.matches&&!open;
    main.inert=small.matches&&open;
    backdrop.hidden=!open||!small.matches;
    toggle.setAttribute('aria-expanded',String(open));
    if(open)sidebar.querySelector('button,a')?.focus();
    else if(restore)toggle.focus();
  }
  toggle?.addEventListener('click',()=>drawer(true));
  sidebar?.querySelector('.nav-close')?.addEventListener('click',()=>drawer(false));
  backdrop?.addEventListener('click',()=>drawer(false));
  small.addEventListener('change',()=>drawer(false,false));drawer(false,false);
  document.addEventListener('keydown',e=>{
    if(!small.matches||!document.body.classList.contains('nav-open'))return;
    if(e.key==='Escape'){e.preventDefault();drawer(false);}
    if(e.key==='Tab'){
      const items=[...sidebar.querySelectorAll('button,a[href]')].filter(x=>x.getClientRects().length);
      const first=items[0],last=items.at(-1);
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    }
  });
  const dialog=document.querySelector('#navDialog'), query=document.querySelector('#navQuery'), results=document.querySelector('#navResults');
  const links=[...document.querySelectorAll('.sidebar nav a')];
  function draw(){
    const matches=links.filter(a=>a.textContent.toLowerCase().includes(query.value.toLowerCase()));
    results.replaceChildren(...matches.map(a=>{const link=document.createElement('a');link.href=a.getAttribute('href');link.textContent=a.textContent;return link;}));
    document.querySelector('#navStatus').textContent=matches.length+' workspaces found';
  }
  function open(){if(!sidebar)return;drawer(false,false);query.value='';draw();dialog.showModal();query.focus();}
  document.querySelector('#quickNav')?.addEventListener('click',open);
  if(!sidebar)document.querySelector('#quickNav').hidden=true;
  query.addEventListener('input',draw);
  document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!dialog.open)open();}});
  document.querySelectorAll('.table-wrap').forEach(el=>{el.tabIndex=0;el.setAttribute('role','region');el.setAttribute('aria-label','Data table; scroll horizontally for more columns');});
  function connection(){document.querySelector('#connectionStatus').hidden=navigator.onLine;}
  addEventListener('online',connection);addEventListener('offline',connection);connection();
});
