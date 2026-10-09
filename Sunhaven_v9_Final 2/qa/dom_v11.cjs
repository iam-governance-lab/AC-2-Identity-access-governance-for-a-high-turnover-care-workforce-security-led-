/* Optional DOM interaction tests. npm install jsdom in a separate QA folder.
   Run with NODE_PATH=<that folder>/node_modules node qa/dom_v11.cjs.
   Layout, native dialogs and browser accessibility are NOT emulated assertions. */
const {JSDOM}=require('jsdom');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const dom=new JSDOM(fs.readFileSync(path.join(root,'evidence/v11/rendered-pages/16-inbox.html'),'utf8'),{url:'http://localhost/notifications',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document;await new Promise(resolve=>w.addEventListener('load',resolve));
 const media={matches:true,addEventListener:(type,fn)=>media.change=fn};w.matchMedia=()=>media;
 w.HTMLElement.prototype.getClientRects=function(){return [{}]};
 const dialog=d.querySelector('#navDialog');dialog.showModal=function(){this.open=true};
 w.eval(fs.readFileSync(path.join(root,'portal/static/app.js'),'utf8'));
 w.eval(fs.readFileSync(path.join(root,'portal/static/v11.js'),'utf8'));
 d.dispatchEvent(new w.Event('DOMContentLoaded'));
 const checks=[];function pass(name){checks.push({scenario:name,result:'PASS'})}
 const main=d.querySelector('main'),side=d.querySelector('.sidebar'),toggle=d.querySelector('.menu-toggle'),back=d.querySelector('.nav-backdrop');
 assert.equal(side.inert,true);assert.equal(main.inert,false);toggle.click();assert.equal(main.inert,true);assert.equal(side.inert,false);assert.equal(back.hidden,false);assert.equal(toggle.getAttribute('aria-expanded'),'true');pass('Mobile drawer opens with background inert');
 const first=side.querySelector('button'),last=[...side.querySelectorAll('button,a[href]')].at(-1);first.focus();d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));assert.equal(d.activeElement,last);last.focus();d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));assert.equal(d.activeElement,first);pass('Drawer focus wraps in both directions');
 d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(main.inert,false);assert.equal(side.inert,true);assert.equal(d.activeElement,toggle);pass('Escape closes drawer and restores trigger focus');
 toggle.click();back.click();assert.equal(back.hidden,true);pass('Backdrop closes navigation');
 media.matches=false;media.change();assert.equal(side.inert,false);assert.equal(main.inert,false);pass('Desktop resize restores navigation and main content');
 d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true,cancelable:true}));assert.equal(dialog.open,true);const q=d.querySelector('#navQuery');assert.equal(d.activeElement,q);q.value='Saved views';q.dispatchEvent(new w.Event('input'));assert.equal(d.querySelectorAll('#navResults a').length,1);assert.equal(d.querySelector('#navResults a').getAttribute('href'),'/saved-views');pass('Keyboard quick navigation filters actual authorized links');
 q.value='no-such-workspace';q.dispatchEvent(new w.Event('input'));assert.match(d.querySelector('#navStatus').textContent,/0 workspaces/);pass('Quick navigation has an announced empty state');
 Object.defineProperty(w.navigator,'onLine',{value:false,configurable:true});w.dispatchEvent(new w.Event('offline'));assert.equal(d.querySelector('#connectionStatus').hidden,false);Object.defineProperty(w.navigator,'onLine',{value:true});w.dispatchEvent(new w.Event('online'));assert.equal(d.querySelector('#connectionStatus').hidden,true);pass('Offline notice appears and clears after reconnection');
 const result={environment:'jsdom '+require('jsdom/package.json').version,limitations:'DOM simulation only; no layout, browser screenshot or native accessibility validation',checks};
 fs.writeFileSync(path.join(root,'evidence/v11/dom-tests.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));w.close();
})().catch(e=>{console.error(e);process.exitCode=1});
