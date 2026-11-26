'use strict';
const $ = id => document.getElementById(id);
const doctorPage = /^\/doctor(?:\.html)?$/.test(location.pathname);
const signIn = '/signin?next=' + (doctorPage ? '/doctor' : '/pilot');
let state, csrf, busy = false, activePatient = '', search = '', reviewOnly = false;
function node(parent, tag, text) {
  const n = document.createElement(tag); if (text) n.textContent = text;
  parent.appendChild(n); return n;
}
function section(title, parent = $('content')) {
  const n = node(parent,'section'); node(n,'h2',title); return n;
}
function button(parent, label, fn) {
  const b = node(parent,'button',label);
  b.onclick = async () => {
    if (busy) return;
    busy = b.disabled = true;
    try { await fn(); } catch (e) { $('message').textContent = e.message; }
    finally { busy = b.disabled = false; }
  };
  return b;
}
function input(parent, title, value = '', multiline = false, max = 300) {
  const label = node(parent,'label',title);
  const n = node(label,multiline ? 'textarea' : 'input'); n.maxLength = max; n.value = value;
  return n;
}
async function api(path, data) {
  const r = await fetch(path,{method:data?'POST':'GET',cache:'no-store',
    headers:{'Content-Type':'application/json','X-CSRF-Token':csrf || ''},body:data?JSON.stringify(data):undefined});
  if (r.status === 401) location.replace(signIn);
  const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Please retry.'); return j;
}
async function refresh(message = '') {
  state = await api('/api/pilot?view=' + (doctorPage ? 'doctor' : 'patient')); render(); $('message').textContent = message;
}
async function act(action, data, message) {
  await api('/api/pilot',{action,...data}); await refresh(message);
}
function lines(parent,d) {
  node(parent,'p','What I want to discuss\n'+d.question);
  node(parent,'p','Medicines\n'+(d.medicines || 'Unknown or skipped'));
  node(parent,'p','Readings\n'+(d.readings || 'Unknown or skipped'));
}
function patient() {
  $('heading').textContent = 'Prepare for my visit';
  const s = section('My visit summary'), draft = state.draft || {};
  const q = input(s,'What would you like to discuss at your appointment?',draft.question,true,800);
  const m = input(s,'Medicines (optional, skip if unsure)',draft.medicines,true,500);
  const r = input(s,'Readings (optional, e.g. blood pressure in mmHg)',draft.readings,true,500);
  const read = () => ({question:q.value.trim(),medicines:m.value.trim(),readings:r.value.trim()});
  button(s,'Save private draft',async()=>{await api('/api/pilot',{action:'draft',...read()}); $('message').textContent='Private draft saved.';});
  let preview;
  s.oninput = () => { if (preview) preview.remove(); };
  button(s,'Preview summary',()=>{
    const data = read(); if (!data.question) {q.focus(); throw new Error('Enter a question for your visit.');}
    if (preview) preview.remove();
    preview = section('Preview your summary'); preview.className='preview'; lines(preview,data);
    button(preview,'Print',()=>window.print());
    for (const v of state.visits) button(preview,'Share with '+state.clinic.name+' · visit '+v.visit.slice(0,8),async()=>{
      await api('/api/pilot',{action:'draft',...data});
      await act('share',{visit:v.visit,version:v.version,...data},'Your clinic received the summary.');
    });
    preview.scrollIntoView();
  });
  if (!state.visits.length) node(s,'p','To share, give your account code below to the clinic for a visit invitation.');
  for (const v of state.visits) {
    const info = section(state.clinic.name+' · visit '+v.visit.slice(0,8));
    node(info,'p',state.clinic.instructions);
    node(info,'p',v.shared ? (v.reviewed ? 'Read by '+v.reviewed.by+' · '+new Date(v.reviewed.time).toLocaleString()+'\nReview means a staff member read this version.' : 'Shared · '+new Date(v.time).toLocaleString()) : 'Private · available to share');
    if (v.shared) {lines(info,v.content); node(info,'p','Withdrawal closes access here. The clinic may already have retained a copy.');
      button(info,'Withdraw sharing',()=>act('withdraw',{visit:v.visit,version:v.version},'Sharing withdrawn.'));}
  }
}
function directory() {
  const patients = new Map();
  for (const item of [...state.roster].sort((a,b)=>b.time-a.time)) {
    if (!patients.has(item.patient)) patients.set(item.patient, []);
    patients.get(item.patient).push(item);
  }
  const area = section('Patient records');
  const tools = node(area,'div'); tools.className = 'record-tools';
  const find = input(tools,'Find a patient',search); find.type='search'; find.placeholder='Search by reference or patient code';
  const filter = node(tools,'label','Review status');
  const select = node(filter,'select');
  node(select,'option','All patients').value='all';
  node(select,'option','Needs review').value='pending';
  select.value=reviewOnly?'pending':'all';
  button(tools,'Refresh records',()=>refresh('Records refreshed.'));
  const layout=node(area,'div'); layout.className='record-layout';
  const list=node(layout,'nav'); list.setAttribute('aria-label','Patients');
  const detail=node(layout,'article'); detail.setAttribute('aria-live','polite');
  function draw() {
    list.replaceChildren(); detail.replaceChildren();
    const query=search.trim().toLowerCase();
    const visible=[...patients].filter(([id,visits])=>
      (id.includes(query) || visits.some(v=>v.reference.toLowerCase().includes(query))) &&
      (!reviewOnly || visits.some(v=>v.status==='Needs review')));
    if (!visible.length) {
      node(detail,'p',patients.size ? 'No patients match this search.' : 'Invite a patient below to start their visit record.'); return;
    }
    if (!visible.some(([id])=>id===activePatient)) activePatient=visible[0][0];
    for (const [id,visits] of visible) {
      const name=visits.find(v=>v.reference)?.reference || 'Patient '+id.slice(-8);
      const row=button(list,name,()=>{activePatient=id;draw();});
      row.setAttribute('aria-current',String(activePatient===id));
      const pending=visits.filter(v=>v.status==='Needs review').length;
      node(row,'small',visits.length+' visit'+(visits.length===1?'':'s')+' · '+(pending ? pending+' to review' : visits[0].status));
      if (activePatient!==id) continue;
      node(detail,'h3',name);node(detail,'p','Patient code ending '+id.slice(-8));
      for (const entry of visits) {
        const card=section(entry.status,detail);
        node(card,'p','Visit '+entry.visit.slice(0,8)+(entry.time?' · '+new Date(entry.time).toLocaleString():''));
        const shared=state.visits.find(v=>v.visit===entry.visit);
        if (!shared) continue;
        lines(card,shared.content);
        if (shared.reviewed) node(card,'p','Read by '+shared.reviewed.by+' · '+new Date(shared.reviewed.time).toLocaleString());
        else button(card,'Mark this version reviewed',()=>act('review',{visit:shared.visit,version:shared.version},'Review recorded.'));
      }
    }
  }
  find.oninput=()=>{search=find.value;draw();};
  select.onchange=()=>{reviewOnly=select.value==='pending';draw();};
  draw();
}
function facility() {
  $('heading').textContent = state.clinic ? state.clinic.name+' · Doctor portal' : 'Doctor portal';
  if (!state.member) node($('content'),'p','Give your account code below to your verified clinic manager for access.');
  if (state.admin && !state.clinic) {
    const s = section('Register verified rehearsal facility');
    const n=input(s,'Verified facility name'), m=input(s,'Verified manager’s account code'), i=input(s,'Review window and contact instructions for urgent concerns');
    button(s,'Register clinic',()=>act('setup',{name:n.value,target:m.value.trim(),instructions:i.value},'Clinic registered.'));
  }
  const privateCases = node($('content'),'a','My private teaching cases'); privateCases.href='/dashboard';
  if (!state.member) return;
  directory();
  const invite = section('Invite a patient to a visit'), target=input(invite,'Patient’s account code');
  const ref=input(invite,'Fictional patient reference (optional)', '', false, 60);
  const visit=crypto.randomUUID();
  button(invite,'Issue visit invitation',async()=>{await act('inviteVisit',{visit,target:target.value.trim(),reference:ref.value.trim()},'Visit invitation ready in the patient workspace.');});
  const lib=section('Facility teaching library');
  const examples=['A fictional visitor brings two home blood pressure readings and asks how to record them.','A fictional visitor wants to understand the cholesterol values on a sample report.','A fictional visitor prepares a medicine list before their appointment.'];
  for (const [i,t] of state.templates.entries()) {
    if (state.library.includes(t)) {node(lib,'h3',t);node(lib,'p',examples[i]);}
    else button(lib,'Add example · '+t,()=>act('library',{template:t},'Example added.'));
  }
  if (state.member === 'manager') {
    const staff=section('Manage staff'), who=input(staff,'Staff account code, verified with its owner');
    button(staff,'Grant staff access',()=>act('inviteStaff',{target:who.value.trim()},'Staff access granted.'));
    for (const member of state.members.filter(x=>x!==state.id)) button(staff,'Remove staff '+member.slice(-8),()=>act('removeStaff',{target:member},'Access removed.'));
  }
}
function render() {
  $('content').replaceChildren();
  if (doctorPage) facility(); else patient();
  const info=node($('content'),'details'); node(info,'summary','My account code');node(info,'p',state.id);
}
$('logout').onclick=async()=>{try{await api('/api/logout',{});location.replace('/signin');}catch(e){$('message').textContent=e.message;}};
window.addEventListener('pageshow', e=>{if(e.persisted) location.reload();});
(async()=>{
  const session=await api('/api/session');
  if (!session.user) return location.replace(signIn);
  csrf=session.csrf;
  window.watchAccountTab(csrf);
  if (doctorPage !== (session.user.accountType === 'facility')) return location.replace('/app');
  await refresh();
})().catch(e=>{$('message').textContent=e.message;});
