'use strict';
const $ = id => document.getElementById(id);
let state, csrf, busy = false;
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
  if (r.status === 401) location.replace('/signin?next=/pilot');
  const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Please retry.'); return j;
}
async function refresh(message = '') {
  state = await api('/api/pilot'); render(); $('message').textContent = message;
}
async function act(action, data, message) {
  await api('/api/pilot',{action,...data}); await refresh(message);
}
function choose() {
  $('heading').textContent = 'Choose your workspace'; $('content').replaceChildren();
  for (const [type,label] of [['patient','I’m a patient'],['facility','I work at a medical facility']]) {
    button($('content'),label,()=>act('workspace',{workspace:type},''));
  }
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
function facility() {
  $('heading').textContent = state.clinic?.name || 'Medical facility workspace';
  if (!state.member) node($('content'),'p','Give your account code below to your verified clinic manager for access.');
  if (state.admin && !state.clinic) {
    const s = section('Register verified rehearsal facility');
    const n=input(s,'Verified facility name'), m=input(s,'Verified manager’s account code'), i=input(s,'Review window and contact instructions for urgent concerns');
    button(s,'Register clinic',()=>act('setup',{name:n.value,target:m.value.trim(),instructions:i.value},'Clinic registered.'));
  }
  const privateCases = node($('content'),'a','My private teaching cases'); privateCases.href='/dashboard';
  if (!state.member) return;
  const invite = section('Invite a patient to a visit'), target=input(invite,'Patient’s account code');
  let visit=crypto.randomUUID();
  button(invite,'Issue visit invitation',async()=>{await act('inviteVisit',{visit,target:target.value.trim()},'Visit invitation ready in the patient workspace.');});
  const inbox=section('Patient submissions');
  if (!state.visits.length) node(inbox,'p','No shared submissions.');
  for (const v of state.visits) {
    const card=section('Visit '+v.visit.slice(0,8)+' · version '+v.version,inbox); lines(card,v.content);
    node(card,'p','Shared '+new Date(v.time).toLocaleString());
    if (v.reviewed) node(card,'p','Read by '+v.reviewed.by);
    else button(card,'Confirm I read this version',()=>act('review',{visit:v.visit,version:v.version},'Review recorded.'));
  }
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
  $('content').replaceChildren(); $('switch').hidden=!state.workspace;
  if (!state.workspace) return choose();
  if (state.workspace==='patient') patient(); else facility();
  const info=node($('content'),'details'); node(info,'summary','My account code');node(info,'p',state.id);
}
$('switch').onclick=choose;
$('logout').onclick=async()=>{try{await api('/api/logout',{});location.replace('/signin');}catch(e){$('message').textContent=e.message;}};
window.addEventListener('pageshow', e=>{if(e.persisted) location.reload();});
(async()=>{
  const session=await api('/api/session');
  if (!session.user) return location.replace('/signin?next=/pilot');
  csrf=session.csrf;
  const choice=location.hash.slice(1);
  if (['patient','facility'].includes(choice)) {await api('/api/pilot',{action:'workspace',workspace:choice});history.replaceState({},'',location.pathname);}
  await refresh();
})().catch(e=>{$('message').textContent=e.message;});
