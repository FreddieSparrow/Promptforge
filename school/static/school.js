async function askSchoolAI(){
  const prompt=document.getElementById('prompt').value.trim();
  if(!prompt)return;
  const mode=document.getElementById('mode').value;
  const room=document.getElementById('room').value;
  const answer=document.getElementById('answer');
  answer.textContent='Thinking...';
  try{
    const r=await fetch('/api/ask',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt,mode,room})
    });
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'Request failed');
    answer.textContent=d.answer;
  }catch(e){
    answer.textContent='Error: '+e.message;
  }
}

async function loadAdminPanel(){
  try{
    const status=await fetch('/api/status').then(r=>r.json());
    document.getElementById('system-status').innerHTML=`
      <strong>Service:</strong> ${status.service}<br>
      <strong>Ollama Running:</strong> ${status.ollama.running}<br>
      <strong>Models:</strong> ${(status.ollama.models||[]).join(', ') || 'None'}
    `;

    const controls=await fetch('/api/admin/settings').then(r=>r.json());
    document.getElementById('admin-mode').value=controls.mode||'classroom';
    document.getElementById('exam-toggle').checked=controls.exam_mode_policy?.enabled||false;
    document.getElementById('coursework-toggle').checked=controls.banned_coursework_mode?.enabled!==false;
  }catch(e){
    document.getElementById('system-status').textContent='Failed to load status: '+e.message;
  }
}

async function saveAdminSettings(){
  const payload={
    mode:document.getElementById('admin-mode').value,
    exam_mode_enabled:document.getElementById('exam-toggle').checked,
    banned_coursework_enabled:document.getElementById('coursework-toggle').checked,
    default_model:document.getElementById('default-model').value
  };

  const status=document.getElementById('save-status');
  status.textContent='Saving...';

  try{
    const r=await fetch('/api/admin/settings',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    });
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||'Save failed');
    status.textContent='Settings saved successfully.';
  }catch(e){
    status.textContent='Error: '+e.message;
  }
}
