(()=>{
  const arena=document.querySelector('.challenge-shell');
  if(!arena) return;

  /* ============================================================
     MOTOR DE AUDIO — síntesis procedural en capas + reverb real
     (sin archivos externos: robusto, rápido de cargar, sin problemas
     de copyright, funciona offline)
     ============================================================ */
  let audioCtx=null, masterBus=null, soundEnabled=localStorage.getItem('xamoxSound')!=='0';
  const AudioCtx=window.AudioContext||window.webkitAudioContext;

  function ctx(){
    if(!AudioCtx||!soundEnabled) return null;
    if(!audioCtx){
      audioCtx=new AudioCtx();
      masterBus=audioCtx.createGain(); masterBus.gain.value=.8;
      masterBus.connect(audioCtx.destination);
    }
    if(audioCtx.state==='suspended') audioCtx.resume().catch(()=>{});
    return audioCtx;
  }

  /* Un tono limpio: una sola onda, envolvente simple, sin ruido ni reverb */
  function voice(freq,{dur=.12,type='sine',vol=.08,delay=0,attack=.008}={}){
    const c=ctx(); if(!c) return;
    const o=c.createOscillator(), g=c.createGain();
    const t=c.currentTime+delay;
    o.type=type; o.frequency.setValueAtTime(freq,t);
    g.gain.setValueAtTime(.0001,t);
    g.gain.exponentialRampToValueAtTime(vol,t+attack);
    g.gain.exponentialRampToValueAtTime(.0001,t+dur);
    o.connect(g).connect(masterBus);
    o.start(t); o.stop(t+dur+.03);
  }

  /* Notas musicales reales (Do-Mi-Sol) para que suene afinado, no a pitido random */
  const N={C4:261.6,E4:329.6,G4:392.0,C5:523.3,E5:659.3,G5:784.0,A4:440,D5:587.3};

  const sfx={
    click(){voice(600,{dur:.045,type:'sine',vol:.04})},

    correct(){ // dos notas ascendentes, limpio
      voice(N.E5,{dur:.11,type:'sine',vol:.08});
      voice(N.G5,{dur:.16,type:'sine',vol:.08,delay:.09});
    },

    wrong(){ // una nota grave y corta, sin ruido
      voice(220,{dur:.16,type:'sine',vol:.05});
      voice(180,{dur:.18,type:'sine',vol:.045,delay:.1});
    },

    reward(){ // tres notas ascendentes limpias
      voice(N.C5,{dur:.12,type:'sine',vol:.08});
      voice(N.E5,{dur:.12,type:'sine',vol:.08,delay:.1});
      voice(N.G5,{dur:.22,type:'sine',vol:.09,delay:.2});
    },

    tick(){voice(1000,{dur:.02,type:'sine',vol:.02})},

    spin(){voice(180,{dur:.18,type:'sine',vol:.04})},

    lightning(){voice(140,{dur:.14,type:'sine',vol:.06});voice(700,{dur:.05,type:'sine',vol:.04,delay:.05})},

    lab(){voice(N.E4,{dur:.12,type:'sine',vol:.05});voice(N.A4,{dur:.16,type:'sine',vol:.05,delay:.1})},

    boss(){voice(140,{dur:.3,type:'sine',vol:.07});voice(180,{dur:.28,type:'sine',vol:.05,delay:.1})},

    quiz(){voice(N.A4,{dur:.08,type:'sine',vol:.045});voice(N.D5,{dur:.11,type:'sine',vol:.045,delay:.06})},

    levelup(){voice(N.C5,{dur:.11,type:'sine',vol:.08});voice(N.E5,{dur:.11,type:'sine',vol:.08,delay:.09});voice(N.G5,{dur:.2,type:'sine',vol:.09,delay:.18})}
  };
  function play(name){try{(sfx[name]||sfx.click)();}catch(e){}}

  const top=arena.querySelector('.arena-topline');
  if(top){
    const b=document.createElement('button');
    b.type='button';b.className='sound-toggle';
    const render=()=>b.textContent=soundEnabled?'🔊 Sonido activado':'🔇 Sonido desactivado';render();
    b.addEventListener('click',()=>{soundEnabled=!soundEnabled;localStorage.setItem('xamoxSound',soundEnabled?'1':'0');if(soundEnabled){ctx();play('quiz')}render()});
    top.appendChild(b);
  }

  document.querySelectorAll('.quiz-option').forEach(el=>el.addEventListener('click',()=>play('click')));
  document.querySelectorAll('[data-sfx]').forEach(el=>el.addEventListener('click',()=>play(el.dataset.sfx)));

  const feedback=document.querySelector('[data-feedback-sfx]');
  if(feedback){
    const name=feedback.dataset.feedbackSfx;
    setTimeout(()=>play(name),120);
    if(name==='correct') confetti(26);
  }
  const result=document.querySelector('[data-result-sfx]');
  if(result){
    const outcome=result.dataset.resultSfx||'wrong';
    setTimeout(()=>play(outcome),150);
    if(outcome==='reward') confetti(46);
  }
  document.querySelectorAll('.achievement-chip').forEach((el,i)=>{
    if(i===0 && document.querySelector('.result-hero, .arena-hero')) setTimeout(()=>play('levelup'),400);
  });

  /* ---------- Modo Relámpago ---------- */
  const speed=document.querySelector('[data-speed-game]');
  if(speed){
    const start=document.getElementById('speedStart'),card=document.getElementById('questionCard'),timer=document.getElementById('arenaTimer');
    const form=document.getElementById('arenaAnswerForm'),timed=document.getElementById('timedOut');
    let started=false;
    const begin=()=>{
      if(started) return;started=true;ctx();play('lightning');speed.classList.add('activated');if(card) card.hidden=false;if(start) start.closest('.speed-gate').hidden=true;
      let left=parseInt(speed.dataset.seconds||'25',10);timer.textContent=left;
      const iv=setInterval(()=>{
        left--;timer.textContent=left;
        if(left<=5){timer.closest('.timer-card')?.classList.add('danger');play('tick')}
        if(left<=0){clearInterval(iv);timed.value='1';form.submit()}
      },1000);
    };
    start?.addEventListener('click',begin);
  }

  /* ---------- Ruleta ---------- */
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

  /* ---------- Confeti (ahora con CSS real que lo anima) ---------- */
  function confetti(n){
    const box=document.createElement('div');box.className='arena-confetti';
    for(let i=0;i<n;i++){
      const p=document.createElement('i');
      p.style.left=Math.random()*100+'%';
      p.style.animationDelay=(Math.random()*.4)+'s';
      p.style.setProperty('--drift',(Math.random()*220-110)+'px');
      p.style.transform=`rotate(${Math.random()*360}deg)`;
      box.appendChild(p);
    }
    document.body.appendChild(box);setTimeout(()=>box.remove(),2800);
  }
})();
