from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')
marker = '<!-- NEON-MEGA-INTEGRATION -->'
if marker in text:
    raise SystemExit('Neon integration already present')

text = text.replace('id="quotaValue" type="number" min="0" step="1" value="20"', 'id="quotaValue" type="number" min="0" step="1" value="50"')

panel = r'''
<!-- NEON-MEGA-INTEGRATION -->
<section class="card" id="neonPanel">
<h2>💾 Concurso e salvamento</h2>
<div class="grid">
  <div class="field">
    <label>Número do concurso</label>
    <input id="contestNumber" type="number" min="1" step="1" placeholder="Ex.: 2910">
  </div>
  <div class="field">
    <label>Conta</label>
    <input id="neonEmail" type="email" placeholder="E-mail" autocomplete="username">
  </div>
  <div class="field">
    <label>Senha</label>
    <input id="neonPassword" type="password" placeholder="Senha" autocomplete="current-password">
  </div>
  <div class="field">
    <label>Status</label>
    <div id="neonStatus" class="info-box" style="margin-top:0">Conectando ao banco...</div>
  </div>
</div>
<div class="actions">
  <button id="neonSignIn">🔐 Entrar</button>
  <button id="neonSignUp" class="secondary">Criar conta</button>
  <button id="neonGoogle" class="light">Continuar com Google</button>
  <button id="neonLoad" class="green">📂 Abrir concurso</button>
  <button id="neonSave" class="green">💾 Salvar agora</button>
  <button id="neonLogout" class="red">Sair</button>
</div>
<div id="neonMessage"></div>
</section>
'''
text = text.replace('</header>', '</header>\n\n' + panel, 1)

script = r'''
<script type="module">
const { createClient } = await import('https://esm.sh/@neondatabase/neon-js@0.7.0-beta');

const NEON_AUTH_URL = 'https://ep-sparkling-hat-acujgx9g.neonauth.sa-east-1.aws.neon.tech/neondb/auth';
const NEON_DATA_API_URL = 'https://ep-sparkling-hat-acujgx9g.apirest.sa-east-1.aws.neon.tech/neondb/rest/v1';
const neon = createClient({ auth: { url: NEON_AUTH_URL }, dataApi: { url: NEON_DATA_API_URL } });

let activeContest = Number(localStorage.getItem('megaAnalyzerContest') || 0);
let saveTimer = null;
let restoring = false;

const $ = id => document.getElementById(id);
const msg = (text, type='info-box') => { $('neonMessage').innerHTML = text ? `<div class="${type}">${text}</div>` : ''; };
const sessionData = async () => {
  const result = await neon.auth.getSession();
  return result?.data?.session || result?.session || result?.data || result || null;
};
const currentUser = async () => {
  const s = await sessionData();
  return s?.user || null;
};

function readParticipants(){
  return [...document.querySelectorAll('#participants .participant-row')].map(row=>{
    const inputs=row.querySelectorAll('input');
    return { name: inputs[0]?.value || '', quotas: Math.max(1, Number(inputs[1]?.value || 1)) };
  });
}

function readGames(){
  return [...document.querySelectorAll('#gamesTable tr')].map(row=>{
    const balls=[...row.querySelectorAll('.number-ball')].map(x=>Number(x.textContent.trim())).filter(n=>n>=1&&n<=60);
    return balls;
  }).filter(g=>g.length>=6);
}

function readState(){
  const ids=['quotaValue','betBudget','simpleBetPrice','strategy','generationMode','sixGames','multipleGames','multipleNumbers','prizeSena','otherSena','prizeQuina','prizeQuadra','drawResult'];
  const state={participants:readParticipants(), games:readGames()};
  ids.forEach(id=>{ const el=$(id); if(el) state[id]=el.value; });
  return state;
}

function setValue(id,value){ const el=$(id); if(el && value!==undefined && value!==null) el.value=value; }

async function restoreState(state){
  restoring=true;
  try{
    ['quotaValue','betBudget','simpleBetPrice','strategy','generationMode','sixGames','multipleGames','multipleNumbers','prizeSena','otherSena','prizeQuina','prizeQuadra','drawResult'].forEach(id=>setValue(id,state[id]));
    document.querySelectorAll('#participants .remove').forEach(btn=>btn.click());
    (state.participants||[]).forEach(p=>window.addParticipant(p.name, p.quotas));
    window.clearGames();
    const lines=(state.games||[]).map(g=>g.map(n=>String(n).padStart(2,'0')).join(' ')).join('\n');
    if(lines){ $('manualGames').value=lines; window.addManualGames(); $('manualGames').value=''; }
    if((state.games||[]).length){
      $('resultsSection').classList.remove('hidden');
      if(typeof window.analyzeGames==='function') window.analyzeGames();
      if(typeof window.renderGames==='function') window.renderGames();
    }
    if(state.drawResult && typeof window.checkDraw==='function') window.checkDraw();
    if(typeof window.updateSummary==='function') window.updateSummary();
  } finally { restoring=false; }
}

async function listContests(){
  const user=await currentUser(); if(!user) return [];
  const {data,error}=await neon.from('mega_contests').select('contest_number,updated_at').order('updated_at',{ascending:false});
  if(error) throw error;
  return data||[];
}

async function loadContest(){
  const user=await currentUser();
  if(!user){ msg('Entre na sua conta para abrir ou salvar concursos.','warning'); return; }
  const n=Math.floor(Number($('contestNumber').value));
  if(!n || n<1){ msg('Informe um número de concurso válido.','warning'); return; }
  msg('Carregando concurso...','info-box');
  const {data,error}=await neon.from('mega_contests').select('contest_number,state,updated_at').eq('contest_number',n).limit(1);
  if(error) throw error;
  if(!data?.length){
    activeContest=n; localStorage.setItem('megaAnalyzerContest',String(n));
    await saveContest(true);
    msg(`Concurso ${n} criado e pronto para uso.`,'success');
    return;
  }
  activeContest=n; localStorage.setItem('megaAnalyzerContest',String(n));
  await restoreState(data[0].state||{});
  msg(`Concurso ${n} carregado. As alterações serão salvas automaticamente.`,'success');
}

async function saveContest(silent=false){
  const user=await currentUser();
  if(!user){ if(!silent) msg('Entre na sua conta antes de salvar.','warning'); return; }
  const n=Math.floor(Number($('contestNumber').value||activeContest));
  if(!n || n<1){ if(!silent) msg('Informe o número do concurso antes de salvar.','warning'); return; }
  activeContest=n; localStorage.setItem('megaAnalyzerContest',String(n));
  const state=readState();
  const {data:existing,error:readError}=await neon.from('mega_contests').select('id').eq('contest_number',n).limit(1);
  if(readError) throw readError;
  let error;
  if(existing?.length){
    ({error}=await neon.from('mega_contests').update({state}).eq('contest_number',n));
  }else{
    ({error}=await neon.from('mega_contests').insert({owner_id:user.id,contest_number:n,state}));
  }
  if(error) throw error;
  if(!silent) msg(`Concurso ${n} salvo em ${new Date().toLocaleTimeString('pt-BR')}.`,'success');
}

function scheduleSave(){
  if(restoring || !activeContest) return;
  clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>saveContest(true).catch(e=>msg('Erro ao salvar: '+(e.message||e),'danger')),900);
}

async function refreshAuth(){
  const user=await currentUser();
  if(user){
    $('neonStatus').textContent=`Conectado: ${user.email || user.name || user.id}`;
    $('neonStatus').className='success';
    $('neonEmail').value=user.email || '';
    $('neonPassword').value='';
    if(activeContest) $('contestNumber').value=activeContest;
  }else{
    $('neonStatus').textContent='Não conectado';
    $('neonStatus').className='warning';
  }
}

$('neonSignIn').onclick=async()=>{ try{ const r=await neon.auth.signIn.email({email:$('neonEmail').value.trim(),password:$('neonPassword').value}); if(r?.error) throw r.error; await refreshAuth(); msg('Login realizado.','success'); if(activeContest) await loadContest(); }catch(e){msg('Não foi possível entrar: '+(e.message||e),'danger');} };
$('neonSignUp').onclick=async()=>{ try{ const r=await neon.auth.signUp.email({email:$('neonEmail').value.trim(),password:$('neonPassword').value,name:$('neonEmail').value.trim().split('@')[0]}); if(r?.error) throw r.error; await refreshAuth(); msg('Conta criada. Você já pode usar o Mega Analyzer.','success'); }catch(e){msg('Não foi possível criar a conta: '+(e.message||e),'danger');} };
$('neonGoogle').onclick=async()=>{ try{ await neon.auth.signIn.social({provider:'google',callbackURL:location.href}); }catch(e){msg('Não foi possível iniciar o Google: '+(e.message||e),'danger');} };
$('neonLogout').onclick=async()=>{ await neon.auth.signOut(); activeContest=0; localStorage.removeItem('megaAnalyzerContest'); await refreshAuth(); msg('Você saiu da conta.','info-box'); };
$('neonLoad').onclick=()=>loadContest().catch(e=>msg('Erro ao abrir: '+(e.message||e),'danger'));
$('neonSave').onclick=()=>saveContest(false).catch(e=>msg('Erro ao salvar: '+(e.message||e),'danger'));
$('contestNumber').addEventListener('change',()=>{ if(Number($('contestNumber').value)!==activeContest) msg('Número alterado. Clique em “Abrir concurso” para carregar/criar esse concurso.','warning'); });
document.addEventListener('input',e=>{ if(e.target.matches('#quotaValue,#betBudget,#simpleBetPrice,#strategy,#generationMode,#sixGames,#multipleGames,#multipleNumbers,#prizeSena,#otherSena,#prizeQuina,#prizeQuadra,#drawResult')) scheduleSave(); });
document.addEventListener('change',e=>{ if(e.target.matches('#participants input,#quotaValue,#betBudget,#simpleBetPrice,#strategy,#generationMode,#sixGames,#multipleGames,#multipleNumbers,#prizeSena,#otherSena,#prizeQuina,#prizeQuadra,#drawResult')) scheduleSave(); });

await refreshAuth();
if(activeContest && await currentUser()){ $('contestNumber').value=activeContest; try{ await loadContest(); }catch(e){ msg('Não foi possível carregar o último concurso: '+(e.message||e),'danger'); } }
</script>
'''
text = text.replace('</body>', script + '\n</body>', 1)
path.write_text(text, encoding='utf-8')
print('Neon integration applied')
