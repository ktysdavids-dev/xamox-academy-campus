(()=>{
  const arena=document.querySelector('.challenge-shell');
  if(!arena) return;

  let audioCtx=null;
  let soundEnabled=localStorage.getItem('xamoxSound')!=='0';
  const AudioCtx=window.AudioContext||window.webkitAudioContext;

  function ctx(){
    if(!AudioCtx||!soundEnabled) return null;
    if(!audioCtx) audioCtx=new AudioCtx();
    if(audioCtx.state==='suspended') audioCtx.resume().catch(()=>{});
    return audioCtx;
  }
  function tone(freq,dur=.12,type='sine',vol=.09,delay=0){
    const c=ctx(); if(!c) return;
    const o=c.createOscillator(),g=c.createGain();
    const t=c.currentTime+delay;
    o.type=type;o.frequency.setValueAtTime(freq,t);
    g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(vol,t+.012);g.gain.exponentialRampToValueAtTime(.0001,t+dur);
    o.connect(g).connect(c.destination);o.start(t);o.stop(t+dur+.03);
  }
  function noise(dur=.18,vol=.08){
    const c=ctx(); if(!c) return;
    const len=Math.max(1,Math.floor(c.sampleRate*dur));
    const b=c.createBuffer(1,len,c.sampleRate),data=b.getChannelData(0);
    for(let i=0;i<len;i++) data[i]=(Math.random()*2-1)*(1-i/len);
    const s=c.createBufferSource(),g=c.createGain(),f=c.createBiquadFilter();
    s.buffer=b;f.type='highpass';f.frequency.value=800;g.gain.value=vol;s.connect(f).connect(g).connect(c.destination);s.start();
  }
  const sfx={
    click(){tone(620,.06,'sine',.045)},
    correct(){tone(523,.13,'sine',.09);tone(659,.14,'sine',.09,.1);tone(784,.22,'sine',.1,.2)},
    wrong(){tone(220,.18,'sawtooth',.07);tone(160,.24,'sawtooth',.065,.13)},
    reward(){tone(392,.12,'triangle',.08);tone(523,.12,'triangle',.08,.1);tone(659,.13,'triangle',.08,.2);tone(784,.28,'sine',.1,.3)},
    tick(){tone(980,.035,'square',.025)},
    spin(){tone(180,.25,'triangle',.05)},
    lightning(){noise(.22,.12);tone(95,.34,'sawtooth',.08);tone(880,.08,'square',.06,.04)},
    lab(){tone(330,.14,'sine',.06);tone(440,.18,'sine',.06,.11);tone(554,.22,'sine',.07,.22)},
    boss(){tone(110,.5,'sine',.09);tone(165,.42,'triangle',.07,.12)},
    quiz(){tone(440,.08,'sine',.05);tone(660,.12,'sine',.05,.07)}
  };
  function play(name){try{(sfx[name]||sfx.click)();}catch(e){}}

  const top=arena.querySelector('.arena-topline');
  if(top){
    const b=document.createElement('button');
    b.type='button';b.className='sound-toggle';
    const render=()=>b.textContent=soundEnabled?'🔊 Sonido ON':'🔇 Sonido OFF';render();
    b.addEventListener('click',()=>{soundEnabled=!soundEnabled;localStorage.setItem('xamoxSound',soundEnabled?'1':'0');if(soundEnabled){ctx();play('quiz')}render()});
    top.appendChild(b);
  }

  document.querySelectorAll('.quiz-option').forEach(el=>el.addEventListener('click',()=>play('click')));
  document.querySelectorAll('[data-sfx]').forEach(el=>el.addEventListener('click',()=>play(el.dataset.sfx)));

  const feedback=document.querySelector('[data-feedback-sfx]');
  if(feedback){
    const name=feedback.dataset.feedbackSfx;
    setTimeout(()=>play(name),120);
    if(name==='correct') confetti(22);
  }
  const result=document.querySelector('[data-result-sfx]');
  if(result){const outcome=result.dataset.resultSfx||'wrong';setTimeout(()=>play(outcome),150);if(outcome==='reward') confetti(34)}

  const speed=document.querySelector('[data-speed-game]');
  if(speed){
    const start=document.getElementById('speedStart'),card=document.getElementById('questionCard'),timer=document.getElementById('arenaTimer');
    const form=document.getElementById('arenaAnswerForm'),timed=document.getElementById('timedOut');
    let started=false;
    const begin=()=>{
      if(started) return;started=true;ctx();play('lightning');speed.classList.add('activated');if(card) card.hidden=false;if(start) start.closest('.speed-gate').hidden=true;
      let left=parseInt(speed.dataset.seconds||'25',10);timer.textContent=left;
      const iv=setInterval(()=>{left--;timer.textContent=left;if(left<=5) timer.closest('.timer-card')?.classList.add('danger');if(left<=0){clearInterval(iv);timed.value='1';form.submit()}},1000);
    };
    start?.addEventListener('click',begin);
  }

  const roulette=document.querySelector('[data-roulette]');
  if(roulette){
    const wheel=document.getElementById('rouletteWheel');
    const btn=document.getElementById('spinWheelBtn');
    const coreBtn=document.getElementById('wheelCoreBtn');
    const card=document.getElementById('questionCard');
    const resultBox=document.getElementById('rouletteResult');
    const target=(roulette.dataset.target||'General').trim();
    const pool=[target,'Prompting','Modelos','Workflows','Seguridad','Herramientas','Criterio','Multimodal'];
    const sectors=[...new Set(pool)].slice(0,8);while(sectors.length<8) sectors.push('IA');
    roulette.querySelectorAll('.wheel-label').forEach((el,i)=>{el.textContent=sectors[i];el.style.setProperty('--i',i)});
    const idx=Math.max(0,sectors.indexOf(target));
    let spinning=false;

    const spin=()=>{
      if(spinning) return;
      spinning=true;ctx();play('spin');roulette.classList.add('spinning');
      if(btn){btn.disabled=true;btn.textContent='Girando…'}
      if(coreBtn){coreBtn.disabled=true;const strong=coreBtn.querySelector('strong');if(strong) strong.textContent='...'}
      let ticks=0;
      const tick=setInterval(()=>{play('tick');ticks++;if(ticks>30) clearInterval(tick)},120);
      const angle=360*7 + (360-(idx*45+22.5));
      wheel.style.transform=`rotate(${angle}deg)`;
      setTimeout(()=>{
        clearInterval(tick);play('reward');roulette.classList.remove('spinning');roulette.classList.add('landed');
        if(resultBox){resultBox.hidden=false;resultBox.querySelector('strong').textContent=target}
        if(card){card.hidden=false;card.classList.add('question-reveal');card.scrollIntoView({behavior:'smooth',block:'center'})}
        if(btn) btn.textContent='Ruleta girada ✓';
        if(coreBtn){const strong=coreBtn.querySelector('strong');if(strong) strong.textContent='LISTO'}
      },4800);
    };

    btn?.addEventListener('click',spin);
    coreBtn?.addEventListener('click',spin);
  }

  const lab=document.querySelector('.mode-lab textarea');
  lab?.addEventListener('focus',()=>play('lab'),{once:true});

  function confetti(n){
    const box=document.createElement('div');box.className='arena-confetti';
    for(let i=0;i<n;i++){const p=document.createElement('i');p.style.left=Math.random()*100+'%';p.style.animationDelay=(Math.random()*.35)+'s';p.style.setProperty('--drift',(Math.random()*180-90)+'px');box.appendChild(p)}
    document.body.appendChild(box);setTimeout(()=>box.remove(),2600);
  }
})();
