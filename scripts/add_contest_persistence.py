from pathlib import Path
import re

path = Path('index.html')
text = path.read_text(encoding='utf-8')

# Remove any old authentication panel/integration that may still exist.
text = re.sub(r'\n?<!-- NEON-MEGA-INTEGRATION -->.*?</section>\n\n', '\n', text, count=1, flags=re.S)
marker = '<script type="module">'
start = text.find(marker)
if start != -1:
    end = text.find('</script>', start)
    if end != -1:
        block = text[start:end + len('</script>')]
        if 'neon.auth' in block or 'NEON_AUTH_URL' in block:
            text = text[:start] + text[end + len('</script>'):]

contest_ui = '''
<!-- CONTROLE DO CONCURSO -->
<section class="card" id="contestCard">
<h2>🎟️ Concurso</h2>
<div class="grid">
    <div class="field">
        <label>Número do concurso</label>
        <input id="contestNumber" type="number" min="1" step="1" placeholder="Ex.: 2910">
    </div>
    <div class="field">
        <label>Status</label>
        <div id="contestStatus" class="info-box" style="margin-top:0">Digite o número do concurso.</div>
    </div>
</div>
<div class="actions">
    <button class="green" id="loadContestBtn" type="button">📂 Carregar concurso</button>
    <button class="secondary" id="newContestBtn" type="button">🆕 Novo concurso</button>
    <button id="saveContestBtn" type="button">💾 Salvar agora</button>
</div>
<div class="info-box">
<strong>Como funciona:</strong> cada número de concurso possui seu próprio conjunto de participantes, cotas, valores, configurações, jogos e resultados. Ao voltar a um concurso já cadastrado, os dados são recuperados automaticamente neste dispositivo.
</div>
</section>

'''

if 'id="contestCard"' not in text:
    text = text.replace('<!-- PARTICIPANTES -->', contest_ui + '<!-- PARTICIPANTES -->', 1)

persistence = '''
/* =========================
   PERSISTÊNCIA POR CONCURSO
========================= */

let activeContestNumber = '';
let contestSaveTimer = null;
let contestLoading = false;

function contestStorageKey(number){
    return `megaAnalyzerContest:${String(number).trim()}`;
}

function getContestNumber(){
    const value = String(document.getElementById('contestNumber')?.value || '').trim();
    return /^\\d+$/.test(value) && Number(value) > 0 ? value : '';
}

function collectContestData(){
    return {
        version: 1,
        savedAt: new Date().toISOString(),
        participants: participants.map(p => ({id:p.id, name:p.name, quotas:Number(p.quotas)||1})),
        games: games.map(g => ({type:g.type, numbers:[...g.numbers], combinations:Number(g.combinations)||0, cost:Number(g.cost)||0, origin:g.origin||''})),
        fields: {
            quotaValue: document.getElementById('quotaValue').value,
            betBudget: document.getElementById('betBudget').value,
            simpleBetPrice: document.getElementById('simpleBetPrice').value,
            strategy: document.getElementById('strategy').value,
            generationMode: document.getElementById('generationMode').value,
            sixGames: document.getElementById('sixGames').value,
            multipleGames: document.getElementById('multipleGames').value,
            multipleNumbers: document.getElementById('multipleNumbers').value,
            manualGames: document.getElementById('manualGames').value,
            prizeSena: document.getElementById('prizeSena').value,
            otherSena: document.getElementById('otherSena').value,
            prizeQuina: document.getElementById('prizeQuina').value,
            prizeQuadra: document.getElementById('prizeQuadra').value,
            drawResult: document.getElementById('drawResult').value
        }
    };
}

function updateContestStatus(message,type='info'){
    const box=document.getElementById('contestStatus');
    if(!box)return;
    box.className=type==='success'?'success':type==='danger'?'danger':'info-box';
    box.textContent=message;
}

function saveCurrentContest(showMessage=true){
    if(contestLoading)return false;
    const number=getContestNumber();
    if(!number){updateContestStatus('Digite um número de concurso válido.','danger');return false;}
    try{
        localStorage.setItem(contestStorageKey(number),JSON.stringify(collectContestData()));
        localStorage.setItem('megaAnalyzerLastContest',number);
        activeContestNumber=number;
        if(showMessage)updateContestStatus(`Concurso ${number} salvo neste dispositivo.`,'success');
        return true;
    }catch(error){
        updateContestStatus('Não foi possível salvar os dados neste dispositivo.','danger');
        console.error(error);
        return false;
    }
}

function scheduleContestSave(){
    if(contestLoading||!getContestNumber())return;
    clearTimeout(contestSaveTimer);
    contestSaveTimer=setTimeout(()=>saveCurrentContest(false),350);
}

function clearContestView(){
    contestLoading=true;
    participants=[]; games=[];
    const defaults={quotaValue:'50',betBudget:'0',simpleBetPrice:'5',strategy:'maximum',generationMode:'random',sixGames:'0',multipleGames:'0',multipleNumbers:'7',manualGames:'',prizeSena:'100000000',otherSena:'0',prizeQuina:'0',prizeQuadra:'0',drawResult:''};
    Object.entries(defaults).forEach(([id,value])=>document.getElementById(id).value=value);
    addParticipant('Participante 1',1);
    addParticipant('Participante 2',1);
    renderGames();
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('generationMessage').innerHTML='';
    document.getElementById('manualMessage').innerHTML='';
    document.getElementById('drawResultBox').innerHTML='';
    document.getElementById('prizeResult').innerHTML='';
    document.getElementById('analysisText').innerHTML='';
    updateSummary();
    contestLoading=false;
}

function applyContestData(data){
    contestLoading=true;
    const fields=data.fields||{};
    const defaults={quotaValue:'50',betBudget:'0',simpleBetPrice:'5',strategy:'maximum',generationMode:'random',sixGames:'0',multipleGames:'0',multipleNumbers:'7',manualGames:'',prizeSena:'100000000',otherSena:'0',prizeQuina:'0',prizeQuadra:'0',drawResult:''};
    Object.entries(defaults).forEach(([id,value])=>document.getElementById(id).value=fields[id]!==undefined?fields[id]:value);
    participants=Array.isArray(data.participants)?data.participants.map(p=>({id:p.id||(Date.now()+Math.random()),name:p.name||'Participante',quotas:Math.max(1,Number(p.quotas)||1)})):[];
    if(!participants.length){participants=[{id:Date.now()+Math.random(),name:'Participante 1',quotas:1},{id:Date.now()+Math.random(),name:'Participante 2',quotas:1}];}
    games=Array.isArray(data.games)?data.games.map(g=>({type:g.type||`${(g.numbers||[]).length} números`,numbers:sortNumbers((g.numbers||[]).map(Number)),combinations:Number(g.combinations)||combination((g.numbers||[]).length),cost:Number(g.cost)||0,origin:g.origin||''})):[];
    renderParticipants();
    updateSummary();
    if(games.length){renderGames();analyzeGames();document.getElementById('resultsSection').classList.remove('hidden');}
    else{renderGames();document.getElementById('resultsSection').classList.add('hidden');}
    contestLoading=false;
}

function loadContest(number=getContestNumber()){
    number=String(number||'').trim();
    if(!/^\\d+$/.test(number)||Number(number)<=0){updateContestStatus('Digite um número de concurso válido.','danger');return;}
    document.getElementById('contestNumber').value=number;
    activeContestNumber=number;
    const raw=localStorage.getItem(contestStorageKey(number));
    if(raw){
        try{applyContestData(JSON.parse(raw));localStorage.setItem('megaAnalyzerLastContest',number);updateContestStatus(`Concurso ${number} carregado.`,'success');return;}
        catch(error){console.error(error);}
    }
    clearContestView();
    localStorage.setItem('megaAnalyzerLastContest',number);
    updateContestStatus(`Concurso ${number}: novo cadastro pronto para receber os dados.`,'success');
}

function startNewContest(){
    const number=getContestNumber();
    if(!number){updateContestStatus('Digite primeiro o número do novo concurso.','danger');return;}
    if(localStorage.getItem(contestStorageKey(number))&&!confirm(`Já existe um cadastro para o concurso ${number}. Deseja limpar e começar novamente?`))return;
    localStorage.removeItem(contestStorageKey(number));
    clearContestView();
    activeContestNumber=number;
    updateContestStatus(`Novo cadastro iniciado para o concurso ${number}.`,'success');
    saveCurrentContest(false);
}

function restoreLastContest(){
    const last=localStorage.getItem('megaAnalyzerLastContest');
    if(last){document.getElementById('contestNumber').value=last;loadContest(last);}
    else{document.getElementById('contestNumber').value='';clearContestView();updateContestStatus('Digite o número do concurso para começar.');}
}

const contestWatchedIds=['quotaValue','betBudget','simpleBetPrice','strategy','generationMode','sixGames','multipleGames','multipleNumbers','manualGames','prizeSena','otherSena','prizeQuina','prizeQuadra','drawResult'];
function installContestAutosave(){
    contestWatchedIds.forEach(id=>{
        const el=document.getElementById(id);
        if(el)el.addEventListener('input',scheduleContestSave);
        if(el&&el.tagName==='SELECT')el.addEventListener('change',scheduleContestSave);
    });
}

const originalRenderParticipants=renderParticipants;
renderParticipants=function(){originalRenderParticipants();if(!contestLoading)scheduleContestSave();};
const originalUpdateParticipant=updateParticipant;
updateParticipant=function(id,key,value){originalUpdateParticipant(id,key,value);scheduleContestSave();};
const originalAddParticipant=addParticipant;
addParticipant=function(name='',quotas=1){originalAddParticipant(name,quotas);scheduleContestSave();};
const originalRemoveParticipant=removeParticipant;
removeParticipant=function(id){originalRemoveParticipant(id);scheduleContestSave();};
const originalRenderGames=renderGames;
renderGames=function(){originalRenderGames();if(!contestLoading)scheduleContestSave();};
const originalClearGames=clearGames;
clearGames=function(){originalClearGames();scheduleContestSave();};
const originalAddManualGames=addManualGames;
addManualGames=function(){originalAddManualGames();scheduleContestSave();};
const originalGenerateGames=generateGames;
generateGames=function(){originalGenerateGames();scheduleContestSave();};
'''

if 'function saveCurrentContest' not in text:
    text=text.replace('/* =========================\n   EVENTOS\n========================= */',persistence+'\n/* =========================\n   EVENTOS\n========================= */',1)

old_init="""addParticipant(
    'Participante 1',
    1
);


addParticipant(
    'Participante 2',
    1
);


updateSummary();"""
new_init="""installContestAutosave();

document.getElementById('loadContestBtn').addEventListener('click',()=>loadContest());
document.getElementById('newContestBtn').addEventListener('click',startNewContest);
document.getElementById('saveContestBtn').addEventListener('click',()=>saveCurrentContest(true));
document.getElementById('contestNumber').addEventListener('change',()=>loadContest());
document.getElementById('contestNumber').addEventListener('keydown',event=>{if(event.key==='Enter')loadContest();});

restoreLastContest();
updateSummary();"""
if old_init in text:
    text=text.replace(old_init,new_init,1)

for item in ['neonEmail','neonPassword','neonSignIn','neonSignUp','neonGoogle','neonForgot','NEON_AUTH_URL','neon.auth']:
    if item in text:
        raise SystemExit(f'Authentication marker still present: {item}')

path.write_text(text,encoding='utf-8')
print('Mega Analyzer updated successfully.')
