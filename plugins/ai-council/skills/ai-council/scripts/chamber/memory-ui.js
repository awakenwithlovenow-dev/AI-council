'use strict';
/* Shared hub helpers escape source/claim strings; no source HTML is executed. */
/* FACTS: the facts screens (Check facts, adding facts on Sources, the facts list on Memory). Hidden at the owner's
   instruction, 15 Oct 2026; the code is kept. Set to true to bring them back. */
const FACTS = false;
document.documentElement.classList.toggle('facts-on', FACTS);
window.MemoryUI = (() => {
  let current = '', sources = null, intake = null, health = null, busy = false;
  let fetchState = {state:'idle'}, fetchTimer = null;
  let uploadResults = [], sourceFilter = '', notice = '', filter = '', staleIds = [], removePath = '', lastRemoval = null;
  const drafts = new Map();
  try { for(const [k,v] of JSON.parse(localStorage.getItem('chamber-memory-drafts')||'[]')) drafts.set(k,v); } catch {}
  function keepDraft(k,v){ drafts.set(k,v);try{localStorage.setItem('chamber-memory-drafts',JSON.stringify([...drafts]));}catch{} }
  const roots = {sources:'sources-root',intake:'intake-root',health:'health-root'};
  const E = esc;
  const btn = (label, attrs='') => `<button class="btn" ${attrs}>${label}</button>`;
  const n = v => Number(v).toLocaleString('en-GB');
  const date = v => v ? String(v).slice(0,10) : 'Date not recorded';
  const noticeHTML = () => notice ? `<p class="memory-notice" role="status">${E(notice)}</p>` : '';
  async function run(action, done){
    if (busy) return;
    busy = true;
    document.querySelectorAll('.memory-page button').forEach(b => b.disabled=true);
    try { await action(); if(done) await done(); }
    catch(e){notice=e.message; const el=document.createElement('p');el.className='memory-notice memory-error';el.setAttribute('role','alert');el.textContent=e.message;$(roots[current])?.prepend(el);}
    finally{busy=false;document.querySelectorAll('.memory-page button:not([data-unavailable])').forEach(b=>b.disabled=false);}
  }
  async function load(page){
    const result = await api(({sources:'/api/sources',intake:'/api/intake',health:'/api/memory-health'})[page]);
    if (page==='sources') { sources=result; try{ fetchState=await api('/api/sources/fetch'); }catch{} }
    if (page==='intake') intake=result;
    if (page==='health') health=result;
    if (current===page) paint();
  }
  function render(page){
    if (!roots[page]) {current='';return;}
    if(current===page)return;
    current=page; notice='';
    $(roots[page]).innerHTML='<p role="status">Reading your council files…</p>';
    load(page).catch(e=>{$(roots[page]).textContent=e.message;});
  }
  function paint(){
    if(current==='sources') paintSources();
    if(current==='intake') paintIntake();
    if(current==='health') paintHealth();
  }
  const STATUS={current:'In force',proposed:'Proposed, not approved',unresolved:'Not settled',historical:'Past',superseded:'Replaced',withdrawn:'Withdrawn'};
  const WHO={owner:'You (as the source records it)',council:'The council',record:'A document on file','ai-draft':'An AI draft'};
  const status=r=>`${E(STATUS[r.status]||r.status||'Unknown')} · ${r.verified?'confirmed by you':'not yet confirmed by you'}`;
  const who=r=>r.verified&&r.authority==='owner'?'You':E(WHO[r.authority]||r.authority||'Not known');
  function sourceButton(source){
    const match=/^(.*):(\d+)(?:[-–]\d+)?$/.exec(source||'');
    const name=match?match[1].split('/').pop().replace(/\.md$/i,''):'';
    return match ? `<button class="link claim-source" data-source="${E(match[1])}" data-line="${match[2]}" title="${E(source)}">Read the source: ${E(name)}, line ${E(match[2])}</button>` : `<p class="muted">Source: ${E(source || 'not recorded')}</p>`;
  }
  function wireSources(root){
    root.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>openSource(b.dataset.source,Number(b.dataset.line||1)));
  }
  async function openSource(path,line){
    const dialog=$('source-dialog');$('source-title').textContent=path;$('source-content').textContent='Reading the source…';dialog.showModal();
    try{
      const data=await api('/api/source?path='+encodeURIComponent(path)+'&line='+line);
      $('source-content').innerHTML=`<p>${data.line_exists ? `Showing lines ${data.start} to ${data.start+data.lines.length-1} of ${data.total}. Line ${line} is highlighted.` : `The cited line ${line} is beyond this file's ${data.total} lines. Check the citation.`}</p><pre>${data.lines.map((s,i)=>`<span class="source-line ${data.start+i===line?'target':''}"><b>${data.start+i}</b>${E(s)}</span>`).join('')}</pre>`;
    }catch(e){$('source-content').textContent=e.message;}
  }
  $('source-dialog').querySelector('[data-source-close]').onclick=()=>$('source-dialog').close();
  $('source-remove-cancel').onclick=()=>$('source-remove-dialog').close();
  $('source-remove-confirm').onclick=()=>run(async()=>{const result=await api('/api/sources/remove',{path:removePath});lastRemoval=result;$('source-remove-dialog').close();notice='Source archived. Claims and answers remain.';await load('sources');});
  function fetchHTML(){
    const f=fetchState||{};
    if(f.state==='running')return `<p class="memory-notice" role="status">Working: ${E(f.step||'starting')}. This can take a few minutes; you can leave this page and come back.</p>`;
    if(f.state==='failed')return `<p class="memory-notice memory-error" role="alert">${E(f.message||'That did not work.')}</p>`;
    if(f.state==='done'){
      const a=f.added||[],d=f.duplicates||[];
      return `<div class="memory-notice" role="status"><p>${a.length?`Brought in ${a.length===1?'1 source. It is':a.length+' sources. They are'} listed below.`:'Nothing new was brought in.'}${d.length?` ${d.length} ${d.length===1?'was':'were'} already here.`:''}</p>${a.length?`<ul>${a.map(s=>`<li>${E(String(s).split('/').pop())}</li>`).join('')}</ul>`:''}${f.message?(a.length?`<details><summary>Claude's note</summary><p class="muted">${E(f.message)}</p></details>`:`<p class="muted">${E(f.message)}</p>`):''}</div>`;
    }
    return '';
  }
  function pollFetch(){
    clearTimeout(fetchTimer);
    fetchTimer=setTimeout(async()=>{
      try{fetchState=await api('/api/sources/fetch');}catch{return pollFetch();}
      if(current!=='sources')return;
      if(fetchState.state==='running'){const s=$('fetch-status');if(s)s.innerHTML=fetchHTML();pollFetch();}
      else{keepDraft('fetch-request','');await load('sources');}
    },3000);
  }
  function paintSources(){
    const list=sources.sources.filter(r=>!sourceFilter || (r.name+' '+r.stored+' '+r.original).toLowerCase().includes(sourceFilter.toLowerCase()));
    $('sources-root').innerHTML=`<h1>Sources</h1><p class="lead">Bring in the material your council should know. Keep the original, then check what it says.</p>
      <div class="upload-zone" id="source-drop"><h2>Add files or a folder</h2><p class="muted">Markdown, text, HTML and Word (.docx). Up to 8 MB per file. Original files are kept; the council reads a text copy.</p>
      <div class="memory-actions">${btn('Choose files','id="pick-sources"')}${btn('Choose a folder','id="pick-folder"')}</div>
      <input hidden type="file" multiple id="source-files" accept=".md,.txt,.html,.htm,.docx"><input hidden type="file" multiple webkitdirectory id="source-folder">
      <p class="muted">You can also drop files or a folder here.</p></div>
      ${uploadResults.length?`<ul class="upload-results" aria-live="polite">${uploadResults.map(r=>`<li class="${r.refused?'refused':''}">${E(r.message)}</li>`).join('')}</ul>`:''}
      <section class="memory-panel" id="fetch-panel"><h2>Bring in from a connected app</h2>
      <p class="muted">Your Claude reads from the apps you have connected, such as Gmail, Google Drive, Notion, Slack or your meeting notes, and saves what you ask for here as sources. It only reads: it cannot send, change or delete anything. Each time uses some of your Claude plan.</p>
      <div class="fetch-grid"><div><label for="fetch-app">From</label><select id="fetch-app">${['','Gmail','Google Drive','Google Calendar','Notion','Slack','Zoom','Granola','Fireflies','Otter'].map(v=>`<option value="${E(v)}" ${v===(drafts.get('fetch-app')||'')?'selected':''}>${v||'Any connected app'}</option>`).join('')}</select></div>
      <div><label for="fetch-request">What to bring in</label><textarea id="fetch-request" rows="3" placeholder="For example: my last five meeting notes about the retreat">${E(drafts.get('fetch-request')||'')}</textarea></div></div>
      <div class="memory-actions"><button class="btn primary" id="fetch-start" type="button">Bring it in</button></div>
      <div id="fetch-status" aria-live="polite">${fetchHTML()}</div>
      <details><summary>If an app cannot be reached</summary><p class="muted">Apps have to be signed in for Claude Code, which is separate from claude.ai. Open a terminal, type <b>claude</b>, then <b>/mcp</b>, choose the app and sign in. Then try again here.</p></details></section>
      ${noticeHTML()}${lastRemoval?`<div class="memory-notice">Archived ${E(lastRemoval.stored)}. ${btn('Undo removal','id="source-undo-last"')}</div>`:''}
      <section class="memory-panel" data-facts><h2>Turn sources into facts you can check</h2>
      <ol class="fact-steps"><li>Copy the prompt and give it to your own Claude, together with the files you added.</li><li>Paste the lines Claude gives back into the box below, then press Add these facts.</li><li>Check them one by one in Check facts.</li></ol>
      <div class="memory-actions">${btn('Copy the prompt','id="copy-extract"')}</div>
      <details id="extract-details"><summary>Show the prompt</summary><pre id="extract-prompt">${E(sources.prompt)}</pre></details>
      <label for="claims-paste">Lines from Claude</label><textarea id="claims-paste" rows="5" placeholder='One line per fact, each starting with {"id": ...'>${E(drafts.get('claims-paste')||'')}</textarea>
      <div class="memory-actions">${btn('Add these facts','id="claims-import"')}</div><p class="muted">Only new facts are added, all marked not yet confirmed. Nothing already here is changed.</p></section>
      <h2>What the council holds</h2><p class="muted">${n(sources.sources.filter(r=>r.held).length)} files.</p>
      <label for="source-search">Find a source</label><input id="source-search" type="search" value="${E(sourceFilter)}" placeholder="Name or folder">
      <div id="source-list">${list.length?list.map(r=>`<article class="source-row"><div><div class="source-name">${E(r.name)}</div><p>${r.added?'Added '+E(date(r.added))+' · ':''}${E(size(r.size))}${!r.held?' · Removed':''}</p><p class="source-path">${E(r.stored)}</p>${r.registered&&(r.origin||r.original)?`<p class="source-path">From: ${E(r.origin||r.original)}</p>`:''}${r.duplicates.length?`<p><span class="badge">Identical file</span> Also held at ${r.duplicates.map(E).join(', ')}</p>`:''}</div><div class="memory-actions">${r.held?btn('Read',`data-source="${E(r.stored)}"`)+btn('Remove',`data-remove-source="${E(r.stored)}" aria-label="Remove ${E(r.name)}"`):r.undo?btn('Undo removal',`data-undo-source="${E(r.undo)}"`):''}</div></article>`).join(''):'<p class="muted">No sources match. Add a file above or clear the search.</p>'}</div>
`;
    $('pick-sources').onclick=()=>$('source-files').click();$('pick-folder').onclick=()=>$('source-folder').click();
    $('source-files').onchange=e=>upload([...e.target.files],'File picker');$('source-folder').onchange=e=>upload([...e.target.files],'Folder picker');
    $('source-search').oninput=e=>{sourceFilter=e.target.value;const position=e.target.selectionStart;paintSources();$('source-search').focus();try{$('source-search').setSelectionRange(position,position);}catch{}};
    $('fetch-app').onchange=e=>keepDraft('fetch-app',e.target.value);
    $('fetch-request').oninput=e=>keepDraft('fetch-request',e.target.value);
    $('fetch-start').disabled=fetchState.state==='running';
    $('fetch-start').onclick=()=>run(async()=>{fetchState=await api('/api/sources/fetch',{app:$('fetch-app').value,request:$('fetch-request').value});$('fetch-status').innerHTML=fetchHTML();$('fetch-start').disabled=true;pollFetch();});
    if(fetchState.state==='running')pollFetch();
    $('claims-paste').oninput=e=>keepDraft('claims-paste',e.target.value);
    $('claims-import').onclick=()=>run(async()=>{const r=await api('/api/intake/import',{text:$('claims-paste').value});keepDraft('claims-paste','');notice=`${r.added} fact${r.added===1?'':'s'} added. They are waiting for you in Check facts.`;await load('sources');});
    $('copy-extract').onclick=async()=>{try{await navigator.clipboard.writeText(sources.prompt);notice='Prompt copied. Paste it into your own Claude with your files.';paintSources();}catch{$('extract-details').open=true;notice='Clipboard unavailable. Select and copy the visible prompt.';const p=document.createElement('p');p.textContent=notice;$('extract-details').append(p);}};
    const root=$('sources-root');wireSources(root);
    root.querySelectorAll('[data-remove-source]').forEach(b=>b.onclick=()=>{removePath=b.dataset.removeSource;$('source-remove-text').textContent=removePath;$('source-remove-dialog').showModal();});
    root.querySelectorAll('[data-undo-source]').forEach(b=>b.onclick=()=>undoSource(b.dataset.undoSource));
    if($('source-undo-last'))$('source-undo-last').onclick=()=>undoSource(lastRemoval.token);
    const drop=$('source-drop');['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('over');}));
    drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
    drop.addEventListener('drop',async e=>{e.preventDefault();drop.classList.remove('over');if(busy)return;const items=[...e.dataTransfer.items];const files=[];try{for(const item of items){const entry=item.webkitGetAsEntry?.();if(entry)await walk(entry,files);else{const f=item.getAsFile();if(f)files.push(f);}}if(!items.length)files.push(...e.dataTransfer.files);await upload(files,'Dropped file or folder');}catch(err){notice=err.message;paintSources();}});
  }
  async function walk(entry,files){
    if(entry.isFile){files.push(await new Promise((yes,no)=>entry.file(yes,no)));return;}
    const reader=entry.createReader();let batch;
    do{batch=await new Promise((yes,no)=>reader.readEntries(yes,no));for(const e of batch)await walk(e,files);}while(batch.length);
  }
  async function undoSource(token){await run(async()=>{await api('/api/sources/undo',{token});lastRemoval=null;notice='Source restored.';await load('sources');});}
  async function upload(files,origin){
    await run(async()=>{uploadResults=[];for(const f of files){
      if(f.size>sources.max_bytes){uploadResults.push({refused:true,message:`${f.name}: refused, larger than 8 MB (8,000,000 bytes).`});continue;}
      if(!/\.(md|txt|html?|docx)$/i.test(f.name)){uploadResults.push({refused:true,message:`${f.name}: type refused. Use md, txt, html or docx.`});continue;}
      try{const response=await fetch('/api/sources/upload',{method:'POST',headers:{'X-Chamber':'1','X-Filename':encodeURIComponent(f.name),'X-Source-Origin':encodeURIComponent(f.webkitRelativePath||origin)},body:f});const d=await response.json();if(!response.ok)throw new Error(d.error);uploadResults.push({message:d.message});}
      catch(e){uploadResults.push({refused:true,message:`${f.name}: ${e.message}`});}
    }notice='Adding files finished. Review the results above.';await load('sources');});
  }
  function claimCard(r,key,conflict){return `<article class="claim-card" tabindex="-1"><span class="badge">${status(r)}</span><p class="claim-text">${E(r.claim)}</p>
    <dl><dt>Who said it</dt><dd>${who(r)}</dd><dt>When</dt><dd>${E(r.effective&&r.effective!=='unknown'?r.effective:'Not known')}</dd><dt>Applies to</dt><dd>${E(r.scope||'Not stated')}</dd></dl>
    ${sourceButton(r.source)}${conflict?btn('This one is right',`data-answer="pick" data-claim="${E(r.id)}"`):''}
    <details class="edit-block"><summary>Edit this fact</summary><label for="edit-${E(r.id)}">Corrected wording</label><textarea rows="4" id="edit-${E(r.id)}" data-draft="${E(r.id)}">${E(drafts.get(r.id)??r.claim)}</textarea><p class="muted">Saving marks your wording as confirmed. The old wording is kept in the history.</p>${btn('Save my wording',`data-answer="edited" data-claim="${E(r.id)}"`)}</details></article>`;}
  function selectedGroups(){return intake.groups.filter(g=>!filter||g.rows.some(r=>r.id===filter||r.entity===filter||(filter==='stale'&&staleIds.includes(r.id))));}
  function paintIntake(){
    const p=intake.progress,sit=intake.sitting,active=sit&&!sit.closed&&sit.count<intake.cap;
    const group=active?selectedGroups()[0]:null;
    $('intake-root').innerHTML=`<h1>Check facts</h1><p class="lead">The facts your council works from, one at a time. Confirm what is right, correct what is wrong, and say when something is out of date.</p>
      <div class="progress-line" id="intake-progress"><span><b>${p.verified} of ${p.current}</b> facts in force confirmed by you</span><span><b>${p.open}</b> still to check</span></div>
      ${noticeHTML()}${filter?`<p class="memory-notice">Focused review: ${E(filter)}. ${btn('Show all questions','id="clear-intake-filter"')}</p>`:''}
      ${!active?`<section class="memory-panel"><h2>${sit?'Saved for now':'Check a few facts'}</h2><p class="muted">${sit?`You answered ${sit.count} last time. `:''}Up to ${intake.cap} at a time. Each answer saves at once, and you can stop whenever you like. Not sure leaves a fact unconfirmed; it never becomes a ruling.</p>${p.open?`<button class="btn primary" id="start-intake">${sit?'Check some more':'Start checking'}</button>`:'<p>Nothing is waiting. You can still read every fact below.</p>'}</section>`:
      `<p class="muted">${sit.count} of ${intake.cap} done. ${btn('Done for now','id="finish-intake"')}</p>${group?`<h2>${group.kind==='conflict'?'Which of these is right?':'Is this right?'}</h2>${group.kind==='conflict'?'<p class="muted">These say different things about the same subject. They may both be true in different cases. Choosing one confirms it and withdraws the other.</p>':''}<div class="claim-grid ${group.kind==='claim'?'single':''}">${group.rows.map(r=>claimCard(r,group.key,group.kind==='conflict')).join('')}</div><div class="answer-buttons">${(group.kind==='claim'?[['yes','Yes, right'],['no','No, wrong'],['outdated','True then, not now'],['unsure','Not sure']]:[['both','Both, in different cases'],['neither','Neither'],['unsure','Not sure']]).map(([a,label])=>`<button class="btn" data-answer="${a}" data-claim="${E(group.rows[0].id)}">${label}</button>`).join('')}</div>${group.kind==='claim'?'<p class="muted">True then, not now: for something that was right at the time, such as the terms of a past launch. It is kept as history.</p>':''}<label for="intake-note" style="margin-top:18px">A note, if it helps (optional)</label><textarea id="intake-note" rows="2">${E(drafts.get('note:'+group.key)||'')}</textarea>`:'<section class="memory-panel"><h2>Nothing else in this sitting</h2><p>Uncertain claims stay open for another sitting. Finish for now, or clear a focused review to see other questions.</p></section>'}`}
      <details class="claim-history"><summary>All ${p.total} facts, including history</summary><label for="claim-search">Find a fact</label><input id="claim-search" type="search" placeholder="A word, a number or an ID"><div id="claim-history-list"></div></details>`;
    if($('start-intake'))$('start-intake').onclick=()=>run(async()=>{await api('/api/intake/start',{});notice='';await load('intake');});
    if($('finish-intake'))$('finish-intake').onclick=()=>run(async()=>{await api('/api/intake/finish',{sitting:sit.id});notice='Progress saved. You can stop here.';await load('intake');});
    if($('clear-intake-filter'))$('clear-intake-filter').onclick=()=>{filter='';paintIntake();};
    const root=$('intake-root');wireSources(root);
    root.querySelectorAll('[data-draft]').forEach(t=>t.oninput=()=>keepDraft(t.dataset.draft,t.value));
    if($('intake-note'))$('intake-note').oninput=e=>keepDraft('note:'+group.key,e.target.value);
    root.querySelectorAll('[data-answer]').forEach(b=>b.onclick=()=>run(async()=>{
      const result=await api('/api/intake/answer',{sitting:sit.id,key:group.key,id:b.dataset.claim,answer:b.dataset.answer,note:$('intake-note')?.value||'',text:$('edit-'+b.dataset.claim)?.value});
      notice=b.dataset.answer==='unsure'?'Saved as not sure. It stays unconfirmed.':b.dataset.answer==='outdated'?'Kept as history. You can still find it under All facts.':`Saved. ${result.sitting.count} of ${intake.cap} done.`;
      await load('intake');$('intake-progress').scrollIntoView({block:'start'});$('intake-root').querySelector('.claim-card')?.focus({preventScroll:true});
    }));
    const history=()=>{const q=$('claim-search').value.toLowerCase();$('claim-history-list').innerHTML=intake.rows.filter(r=>(r.id+' '+r.claim+' '+r.status).toLowerCase().includes(q)).map(r=>`<article><span class="badge">${E(r.id)} · ${status(r)}</span><p>${E(r.claim)}</p>${sourceButton(r.source)}</article>`).join('');wireSources($('claim-history-list'));};
    $('claim-search').oninput=history;history();
  }
  function paintHealth(){
    const h=health,p=h.progress;
    const pulled=/Memory pull: (\d+) block/.exec(h.last_receipt||'');
    $('health-root').innerHTML=`<h1>Memory</h1><p class="lead">What your council knows, and what still needs your eye.</p>${noticeHTML()}
      <div class="health-summary"><div><strong>${n(h.core_chars)}</strong><span>characters every member reads at every turn</span></div><div><strong>${n(h.archive_chars)}</strong><span>characters in the library, brought in by topic</span></div><div data-facts><strong>${p.verified} of ${p.current}</strong><span>facts in force confirmed by you</span></div></div>
      <details><summary>About these numbers</summary><p class="muted">The first figure counts the charter, brief, agenda, latest minutes, rulings, the recent decisions and the largest member file. It leaves out the meeting's own conversation, so a real turn is longer. The library is the member dossiers and the inputs folder.</p></details>
      <section class="memory-panel"><h2>What needs your eye</h2>
      <div class="health-warning" data-facts><p>${p.open} facts are waiting to be checked.</p><a class="btn" href="#intake">Check facts</a></div>
      ${h.conflicts.length?`<div class="health-warning" data-facts><p>${h.conflicts.length} subject${h.conflicts.length===1?' has':'s have'} two facts in force that say different things. They may both be right in different cases.</p>${h.conflicts.map(g=>`<p>${E(g.entity)} ${btn('Look at these',`data-review="${E(g.entity)}"`)}</p>`).join('')}</div>`:''}
      <div class="health-warning" data-facts><p>${h.stale.length} facts in force are more than three months old and not yet confirmed by you. Many may be past launch terms: mark those True then, not now.</p>${h.stale.length?btn('Look at the older facts','data-review="stale"'):''}</div>
      ${!FACTS&&!h.duplicates.length?'<p class="muted">Nothing needs you here.</p>':''}${h.duplicates.length?`<div class="health-warning"><p>${h.duplicates.length} files are held twice, once in member dossiers and once in inputs.</p><details><summary>Show them</summary><p class="muted">Nothing has been removed. If you want one copy, open Sources and remove the other; it can be undone.</p>${h.duplicates.map(g=>`<p class="source-path">${g.map(E).join('<br>')}</p>`).join('')}<a class="btn" href="#sources">Open Sources</a></details></div>`:''}</section>
      <section class="memory-panel"><h2>Memory tools</h2><form id="memory-settings"><div class="health-settings">${[['memory_pull_chars','Library pull','Before each meeting, the passages from the library that match the topic or agenda are added for every member, each with its file and line. Suggested: on, 14,000.',60000],['claims_ledger_chars','Facts list','Adds the matching facts, with their status and date. Suggested: off until most facts are checked.',20000]].map(([key,label,help,max])=>`<div${key==='claims_ledger_chars'?' data-facts':''}><label><input type="checkbox" id="${key}-on" ${h.settings[key]>0?'checked':''}>${label}</label><p class="muted">Now ${h.settings[key]>0?'on':'off'}. ${help}</p><details><summary>Size</summary><label for="${key}-budget">Characters when on</label><input type="number" min="1" max="${max}" step="1" required id="${key}-budget" value="${h.settings[key]>0?h.settings[key]:key==='memory_pull_chars'?14000:5000}"><p class="muted">Up to ${n(max)}. A larger size costs more of your plan at every turn.</p></details></div>`).join('')}</div>
      <p class="muted">${pulled?`The last meeting drew ${pulled[1]} passage${pulled[1]==='1'?'':'s'} from the library.`:'No meeting has used the library pull yet.'}</p><details><summary>What the tests showed</summary><p class="muted">In test meetings on 15 Oct the library pull helped the council restore recorded facts it otherwise missed; the clearest gain was on launch details. The tests were small. Since 15 Oct the pull also searches agenda meetings item by item. ${FACTS?'The facts list has not shown a gain yet.':''}</p></details>
      <div class="memory-actions"><button class="btn primary" type="submit">Save</button>${btn('Refresh','type="button" id="refresh-health"')}</div></form>
      ${h.last_setting&&!h.last_setting.undone?`<p class="memory-notice">Before your last change: library pull ${h.last_setting.before.memory_pull_chars>0?'on':'off'}, facts list ${h.last_setting.before.claims_ledger_chars>0?'on':'off'}. ${btn('Undo that change','id="undo-settings"')}</p>`:''}</section>
      <section class="memory-panel"><h2>The record</h2><p>${h.sources_held} files held.</p><h3 data-facts>Facts by status</h3><table class="health-table" data-facts><thead><tr><th>Status</th><th>Facts</th></tr></thead><tbody>${Object.entries(h.statuses).map(([s,count])=>`<tr><td>${E(STATUS[s]||s)}</td><td>${count}</td></tr>`).join('')||'<tr><td>No claims yet</td><td>0</td></tr>'}</tbody></table><details><summary>Size of each file every member reads</summary><table class="health-table"><tbody>${h.core.map(r=>`<tr><td>${E(r.file)}</td><td>${n(r.chars)} chars</td></tr>`).join('')}<tr><td>Largest seat</td><td>${n(h.largest_seat)} chars</td></tr></tbody></table></details><details><summary>Last library pull, in full</summary>${h.last_receipt?`<pre>${E(h.last_receipt)}</pre>`:'<p class="muted">None yet.</p>'}</details></section>`;
    $('health-root').querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>{filter=b.dataset.review;staleIds=h.stale;go('intake');});
    $('memory-settings').onsubmit=e=>{e.preventDefault();run(async()=>{const values={};for(const k of ['memory_pull_chars','claims_ledger_chars']) values[k]=$(k+'-on').checked?Number($(k+'-budget').value):0;const result=await api('/api/memory-settings',{values,expected:h.settings});notice='Saved. You can undo this below.';await load('health');});};
    $('refresh-health').onclick=()=>run(()=>load('health'));
    if($('undo-settings'))$('undo-settings').onclick=()=>run(async()=>{await api('/api/memory-settings/undo',{token:h.last_setting.token});notice='Previous settings restored.';await load('health');});
  }
  return {render};
})();
window.MemoryUI.render(S.page);

/* Look: Classic (the hub as built), Plain. Chosen in the sidebar, remembered in this browser. */
(function(){
  const SKINS={classic:{name:'Classic',css:''},plain:{name:'Plain',css:'theme-plain.css'}};
  const KEY='council-skin';
  let link=document.getElementById('skin');
  const shipped=link?link.getAttribute('href'):'';               // the template ships with the plain look already linked
  const fallback=Object.keys(SKINS).find(k=>SKINS[k].css===shipped)||'classic';
  let chosen=fallback;
  try{const v=localStorage.getItem(KEY);if(v&&SKINS[v])chosen=v;}catch(e){}
  function apply(k){
    if(!link){link=document.createElement('link');link.rel='stylesheet';link.id='skin';document.head.appendChild(link);}
    const css=SKINS[k].css;
    if(css)link.setAttribute('href',css);else link.removeAttribute('href');
    link.disabled=!css;
    document.documentElement.setAttribute('data-skin',k);
    try{localStorage.setItem(KEY,k);}catch(e){}
  }
  apply(chosen);
  function mount(){
    const box=document.querySelector('.side-links');
    if(!box||document.getElementById('skin-picker'))return;
    const wrap=document.createElement('div');
    wrap.style.cssText='margin-top:10px;font-size:14px';
    const lab=document.createElement('label');lab.htmlFor='skin-picker';lab.textContent='Look';lab.style.cssText='display:block;margin-bottom:4px;font-weight:600';
    const sel=document.createElement('select');sel.id='skin-picker';sel.style.cssText='width:100%;min-height:36px;padding:4px 8px;font-size:15px;border-radius:6px';
    Object.keys(SKINS).forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=SKINS[k].name;if(k===chosen)o.selected=true;sel.appendChild(o);});
    sel.addEventListener('change',()=>{chosen=sel.value;apply(chosen);});
    wrap.appendChild(lab);wrap.appendChild(sel);box.parentNode.appendChild(wrap);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
