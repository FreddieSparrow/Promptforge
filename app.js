let providers={},tones={},selectedTone=null,optimisedText=null;

async function init(){
  try{
    const[pData,tData,sData]=await Promise.all([
      fetch('/api/providers').then(r=>r.json()),
      fetch('/api/tones').then(r=>r.json()),
      fetch('/api/settings').then(r=>r.json())
    ]);
    providers=pData; tones=tData;
    buildProviders(); buildTones(); applySettings(sData);
    checkOllama(); checkUpdates();
  }catch(e){ toast('PromptForge API not reachable: '+e.message); }
}

function applySettings(s){
  document.getElementById('d-ollama-url').value=s.ollama_url||'';
  document.getElementById('d-local-model').dataset.configured=s.local_model||'gemma3:4b';
  setDevMode(s.dev_mode);
  buildKeyInputs(s.providers_configured||[],s.keys_masked||{});
}

function setDevMode(active){
  const pill=document.getElementById('dev-pill'),box=document.getElementById('dev-status-box');
  if(active){pill.style.display='inline-flex';box.className='dev-status active';box.textContent='✓ Developer mode active';}
  else{pill.style.display='none';box.className='dev-status inactive';box.textContent='Developer mode inactive';}
}

function buildProviders(){
  document.getElementById('provider-sel').innerHTML=Object.entries(providers).map(([id,p])=>`<option value="${escAttr(id)}">${esc(p.name)}</option>`).join('');
  onProviderChange();
}

function onProviderChange(){
  const pid=document.getElementById('provider-sel').value;
  document.getElementById('model-sel').innerHTML=(providers[pid]?.models||[]).map(m=>`<option value="${escAttr(m)}">${esc(m)}</option>`).join('');
}

function buildTones(){
  document.getElementById('tone-grid').innerHTML=Object.entries(tones).map(([id,t])=>`<button class="tone-chip" data-id="${escAttr(id)}" onclick="toggleTone('${escJs(id)}',this)">${esc(t.label)}</button>`).join('');
}

function toggleTone(id,btn){
  document.querySelectorAll('.tone-chip').forEach(c=>c.classList.remove('active'));
  if(selectedTone===id){selectedTone=null;document.getElementById('tone-badge').innerHTML='';}
  else{selectedTone=id;btn.classList.add('active');document.getElementById('tone-badge').innerHTML=`<span class="badge">${esc(tones[id].label)}</span>`;}
  updateFinalCard();
}

async function checkOllama(){
  const pill=document.getElementById('ollama-pill'),lbl=document.getElementById('ollama-lbl');
  try{
    const r=await fetch('/api/ollama/status');
    const d=await r.json();
    if(!d.running){pill.className='pill err';lbl.textContent='Ollama unreachable';}
    else if(!d.model_available){pill.className='pill warn';lbl.textContent=d.available_models?.length?'Model missing':'No models installed';}
    else{pill.className='pill ok';lbl.textContent=d.model;}
    populateModelSelect(d);
  }catch(e){pill.className='pill err';lbl.textContent='Status check failed';toast('Could not check Ollama: '+e.message);}
}

async function refreshModels(){
  const sel=document.getElementById('d-local-model');
  sel.innerHTML='<option value="">— loading… —</option>';
  try{const d=await fetch('/api/ollama/status').then(r=>r.json());populateModelSelect(d);}
  catch(e){sel.innerHTML='<option value="">— status check failed —</option>';const hint=document.getElementById('model-hint');if(hint){hint.style.display='block';hint.textContent='PromptForge could not check Ollama: '+e.message;}}
}

function populateModelSelect(ollamaData){
  const sel=document.getElementById('d-local-model');
  const hint=document.getElementById('model-hint');
  const current=sel.dataset.configured||sel.value||ollamaData.model||'gemma3:4b';
  const models=ollamaData.available_models||[];
  if(!ollamaData.running||models.length===0){
    sel.innerHTML='<option value="">— Ollama unreachable or no models pulled —</option>';
    if(current)sel.innerHTML+=`<option value="${escAttr(current)}" selected>${esc(current)} (configured)</option>`;
    if(hint)hint.style.display='block';
    return;
  }
  sel.innerHTML=models.map(m=>{const selected=(m===current||m.split(':')[0]===current.split(':')[0])?' selected':'';return`<option value="${escAttr(m)}"${selected}>${esc(m)}</option>`;}).join('');
  if(current&&!models.includes(current)){sel.innerHTML=`<option value="${escAttr(current)}" selected>${esc(current)} (not pulled)</option>`+sel.innerHTML;}
  if(hint)hint.style.display=models.length<1?'block':'none';
}

async function checkUpdates(){try{const d=await fetch('/api/updates/check').then(r=>r.json());if(d.update_available)document.getElementById('update-pill').classList.add('show');}catch{}}

async function runOptimize(){
  const prompt=document.getElementById('prompt-input').value.trim();
  if(!prompt){toast('Enter a prompt first');return;}
  setCard('original',prompt);setCard('optimised',null,true);
  const btn=document.getElementById('opt-btn');btn.disabled=true;btn.textContent='⏳ Optimising…';
  try{
    const r=await fetch('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
    const d=await r.json().catch(()=>({detail:'Invalid server response'}));
    if(!r.ok)throw new Error(d.detail||'Optimise failed');
    optimisedText=d.optimized;document.getElementById('model-badge').textContent=d.model;setCard('optimised',optimisedText);updateFinalCard();
  }catch(e){setCard('optimised',null,false,'Failed: '+e.message);toast(e.message);}
  finally{btn.disabled=false;btn.textContent='⚡ Optimise Prompt';}
}

function updateFinalCard(){const base=optimisedText||document.getElementById('prompt-input').value.trim();if(!base)return;setCard('final',(selectedTone&&tones[selectedTone])?`${base}\n\n---\n${tones[selectedTone].instruction}`:base);}
function setCard(id,text,loading=false,error=null){const el=document.getElementById('body-'+id);if(loading)el.innerHTML='<span class="ph"><span class="spin"></span> Processing…</span>';else if(error)el.innerHTML=`<span style="color:var(--red)">${esc(error)}</span>`;else if(text)el.textContent=text;}

async function forgeAndSend(){
  const raw=document.getElementById('prompt-input').value.trim();
  if(!raw){toast('Enter a prompt first');return;}
  const provider=document.getElementById('provider-sel').value,model=document.getElementById('model-sel').value;
  setCard('original',raw);
  const btn=document.getElementById('send-btn');btn.disabled=true;btn.textContent='⏳ Forging…';
  let base=raw;setCard('optimised',null,true);
  try{
    const r=await fetch('/api/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:raw})});
    if(r.ok){const d=await r.json();optimisedText=d.optimized;document.getElementById('model-badge').textContent=d.model;setCard('optimised',optimisedText);base=optimisedText;}
    else{setCard('optimised',raw);optimisedText=raw;}
  }catch{setCard('optimised',raw);optimisedText=raw;}
  const finalPrompt=(selectedTone&&tones[selectedTone])?`${base}\n\n---\n${tones[selectedTone].instruction}`:base;
  setCard('final',finalPrompt);
  btn.textContent='⏳ Sending…';switchTab('resp',document.querySelectorAll('.tab-btn')[1]);
  document.getElementById('resp-body').innerHTML='<div class="loading"><div class="spin"></div> Waiting for response…</div>';
  document.getElementById('resp-meta').innerHTML='';
  try{
    const r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:finalPrompt,provider,model,tone:selectedTone})});
    const d=await r.json().catch(()=>({detail:'Invalid server response'}));
    if(!r.ok)throw new Error(d.detail||'Request failed');
    document.getElementById('resp-body').innerHTML=renderMd(d.response);
    const u=d.usage||{};
    document.getElementById('resp-meta').innerHTML=[`<span class="meta-tag">${esc(d.provider)} / ${esc(d.model)}</span>`,u.total_tokens?`<span class="meta-tag">${u.total_tokens} tokens</span>`:'',u.input_tokens?`<span class="meta-tag">${u.input_tokens}→${u.output_tokens}</span>`:''].join('');
  }catch(e){document.getElementById('resp-body').innerHTML=`<span style="color:var(--red)">Error: ${esc(e.message)}</span>`;toast(e.message);}
  finally{btn.disabled=false;btn.textContent='🚀 Forge & Send';}
}

function switchTab(id,btn){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('tab-'+id).classList.add('active');}
function buildKeyInputs(configured,masked){document.getElementById('key-inputs').innerHTML=Object.entries(providers).map(([id,p])=>{const isSet=configured.includes(id);return`<div class="drow"><label>${esc(p.name)} ${isSet?'<span style="color:var(--green)">✓</span>':''}</label><input class="dinput mono" id="key-${escAttr(id)}" type="password" placeholder="${isSet?escAttr(masked[id]||'••••••••'):'sk-…'}" autocomplete="off"></div>`;}).join('');}

async function saveSettings(){
  const keys={};Object.keys(providers).forEach(id=>{const v=document.getElementById(`key-${id}`)?.value||'';if(v)keys[id]=v;});
  await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keys,local_model:document.getElementById('d-local-model').value||document.getElementById('d-local-model').dataset.configured||'gemma3:4b',ollama_url:document.getElementById('d-ollama-url').value||'http://localhost:11434'})});
  const msg=document.getElementById('saved-msg');msg.style.display='block';setTimeout(()=>msg.style.display='none',2000);
  const s=await fetch('/api/settings').then(r=>r.json());applySettings(s);checkOllama();
}

async function pullModel(){
  const input=document.getElementById('pull-model-input'),model=input.value.trim();if(!model){toast('Enter a model name');return;}
  const btn=document.getElementById('pull-btn'),progress=document.getElementById('pull-progress'),statusEl=document.getElementById('pull-status'),bar=document.getElementById('pull-bar'),result=document.getElementById('pull-result');
  btn.disabled=true;btn.textContent='…';progress.style.display='block';result.style.display='none';statusEl.textContent='Connecting…';bar.style.width='0%';
  try{
    const r=await fetch('/api/ollama/pull',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model})});
    if(!r.ok)throw new Error(await r.text());
    const reader=r.body.getReader(),decoder=new TextDecoder();let buffer='';
    while(true){const{done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.trim())continue;const d=JSON.parse(line);if(d.error)throw new Error(d.error);if(d.status)statusEl.textContent=d.status;if(d.total&&d.completed)bar.style.width=Math.round((d.completed/d.total)*100)+'%';else if(d.status==='success')bar.style.width='100%';}}
    progress.style.display='none';result.style.cssText='display:block;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);color:var(--green)';result.textContent=`✓ ${model} installed successfully`;input.value='';await refreshModels();
    const sel=document.getElementById('d-local-model');for(const opt of sel.options){if(opt.value.includes(model.split(':')[0])){sel.value=opt.value;break;}}
  }catch(e){progress.style.display='none';result.style.cssText='display:block;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);color:var(--red)';result.textContent='Error: '+e.message;}
  finally{btn.disabled=false;btn.textContent='Install';}
}

async function activateDev(){const code=document.getElementById('d-dev-code').value,errEl=document.getElementById('dev-err');errEl.style.display='none';try{const r=await fetch('/api/dev/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});if(!r.ok){errEl.textContent='Invalid code';errEl.style.display='block';return;}document.getElementById('d-dev-code').value='';toast('Developer mode activated');setDevMode(true);}catch(e){errEl.textContent=e.message;errEl.style.display='block';}}
async function deactivateDev(){await fetch('/api/dev/deactivate',{method:'POST'});setDevMode(false);toast('Developer mode deactivated');}
function openDrawer(){document.getElementById('overlay').classList.add('open');document.getElementById('drawer').classList.add('open');}
function closeDrawer(){document.getElementById('overlay').classList.remove('open');document.getElementById('drawer').classList.remove('open');}
function copyCard(id){const text=document.getElementById('body-'+id).textContent;if(!text.trim())return;navigator.clipboard.writeText(text).then(()=>toast('Copied!'));}
function toast(msg){const el=document.getElementById('toast');el.textContent=msg;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),2500);}
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function escAttr(s){return esc(s).replace(/"/g,'&quot;');}
function escJs(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");}
function renderMd(raw){const blocks=[],inlines=[];let t=String(raw||'').replace(/```[\w]*\n?([\s\S]*?)```/g,(_,c)=>{blocks.push(c.trim());return`\x00B${blocks.length-1}\x00`;});t=t.replace(/`([^`]+)`/g,(_,c)=>{inlines.push(c);return`\x00I${inlines.length-1}\x00`;});let h=esc(t);h=h.replace(/\x00I(\d+)\x00/g,(_,i)=>`<code>${esc(inlines[i])}</code>`);h=h.replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*\n]+)\*/g,'<em>$1</em>').replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>').replace(/^&gt; (.+)$/gm,'<blockquote>$1</blockquote>').replace(/^[\*\-] (.+)$/gm,'<li>$1</li>').replace(/(<li>[^\n]+<\/li>\n?)+/g,s=>`<ul>${s}</ul>`).replace(/\n\n+/g,'</p><p>');h='<p>'+h+'</p>';h=h.replace(/<p>(<(?:h[123]|pre|ul|blockquote))/g,'$1').replace(/(<\/(?:h[123]|pre|ul|blockquote)>)<\/p>/g,'$1').replace(/\n/g,'<br>').replace(/\x00B(\d+)\x00/g,(_,i)=>`<pre><code>${esc(blocks[i])}</code></pre>`);return h;}

init();
