(()=>{
  const arena=document.querySelector('.challenge-shell');
  if(!arena) return;

  /* ============================================================
     MOTOR DE AUDIO — síntesis procedural en capas + reverb real
     (sin archivos externos: robusto, rápido de cargar, sin problemas
     de copyright, funciona offline)
     ============================================================ */
  let audioCtx=null, masterBus=null, reverbNode=null, soundEnabled=localStorage.getItem('xamoxSound')!=='0';
  const AudioCtx=window.AudioContext||window.webkitAudioContext;

  function buildReverbImpulse(ctx,duration=1.6,decay=2.4){
    const rate=ctx.sampleRate, len=Math.max(1,Math.floor(rate*duration));
    const impulse=ctx.createBuffer(2,len,rate);
    for(let ch=0;ch<2;ch++){
      const data=impulse.getChannelData(ch);
      for(let i=0;i<len;i++) data[i]=(Math.random()*2-1)*Math.pow(1-i/len,decay);
    }
    return impulse;
  }

  function ctx(){
    if(!AudioCtx||!soundEnabled) return null;
    if(!audioCtx){
      audioCtx=new AudioCtx();
      masterBus=audioCtx.createGain(); masterBus.gain.value=1;
      const compressor=audioCtx.createDynamicsCompressor();
      compressor.threshold.value=-18; compressor.knee.value=22; compressor.ratio.value=3.2;
      compressor.attack.value=.004; compressor.release.value=.22;
      reverbNode=audioCtx.createConvolver();
      reverbNode.buffer=buildReverbImpulse(audioCtx);
      const reverbGain=audioCtx.createGain(); reverbGain.gain.value=.16;
      masterBus.connect(compressor); compressor.connect(audioCtx.destination);
      masterBus.connect(reverbNode); reverbNode.connect(reverbGain); reverbGain.connect(compressor);
    }
    if(audioCtx.state==='suspended') audioCtx.resume().catch(()=>{});
    return audioCtx;
  }

  /* Un oscilador con envolvente ADSR suave, timbre por armónicos y salida al bus */
  function voice(freq,{dur=.18,type='sine',vol=.09,delay=0,detune=0,attack=.01,release=null}={}){
    const c=ctx(); if(!c) return;
    const o=c.createOscillator(), g=c.createGain();
    const t=c.currentTime+delay, rel=release??dur*.75;
    o.type=type; o.frequency.setValueAtTime(freq,t); if(detune) o.detune.setValueAtTime(detune,t);
    g.gain.setValueAtTime(.0001,t);
    g.gain.exponentialRampToValueAtTime(vol,t+attack);
    g.gain.exponentialRampToValueAtTime(.0001,t+attack+rel);
    o.connect(g).connect(masterBus);
    o.start(t); o.stop(t+attack+rel+.05);
  }
  /* Acorde: varias voces a la vez con ligera detonación para sonar "real", no MIDI */
  function chord(freqs,opts={}){ freqs.forEach((f,i)=>voice(f,{...opts,delay:(opts.delay||0)+i*.012,detune:(Math.random()*6-3)})); }
  function noiseBurst(dur=.18,vol=.08,filterFreq=800,filterType='highpass'){
    const c=ctx(); if(!c) return;
    const len=Math.max(1,Math.floor(c.sampleRate*dur));
    const b=c.createBuffer(1,len,c.sampleRate), data=b.getChannelData(0);
    for(let i=0;i<len;i++) data[i]=(Math.random()*2-1)*(1-i/len);
    const s=c.createBufferSource(), g=c.createGain(), f=c.createBiquadFilter();
    s.buffer=b; f.type=filterType; f.frequency.value=filterFreq; g.gain.value=vol;
    s.connect(f).connect(g).connect(masterBus); s.start();
  }

  /* Notas musicales reales (Hz) para que los acordes sean armónicos, no pitidos random */
  const N={C4:261.6,E4:329.6,G4:392.0,C5:523.3,E5:659.3,G5:784.0,A4:440,A5:880,D5:587.3,F5:698.5,B4:493.9};

  const sfx={
    click(){voice(660,{dur:.05,type:'sine',vol:.045,attack:.002})},

    correct(){ // arpegio ascendente mayor, cálido
      chord([N.C5],{dur:.16,type:'triangle',vol:.09});
      voice(N.E5,{dur:.16,type:'triangle',vol:.09,delay:.09});
      voice(N.G5,{dur:.26,type:'sine',vol:.1,delay:.18});
    },

    wrong(){ // caída disonante corta, sin ser desagradable
      voice(196,{dur:.2,type:'sawtooth',vol:.06,attack:.004});
      voice(174.6,{dur:.28,type:'sawtooth',vol:.055,delay:.11,attack:.004});
      noiseBurst(.08,.03,1200);
    },

    reward(){ // fanfarria de 4 notas con cola de reverb
      chord([N.C4,N.G4],{dur:.14,type:'triangle',vol:.07});
      voice(N.E5,{dur:.14,type:'triangle',vol:.08,delay:.11});
      voice(N.G5,{dur:.16,type:'triangle',vol:.08,delay:.22});
      chord([N.C5,N.E5,N.G5],{dur:.5,type:'sine',vol:.09,delay:.34,release:.6});
    },

    tick(){voice(1200,{dur:.02,type:'square',vol:.02,attack:.001})},

    spin(){
      voice(160,{dur:.3,type:'triangle',vol:.05});
      noiseBurst(.3,.03,400,'bandpass');
    },

    lightning(){
      noiseBurst(.2,.1,2000,'highpass');
      voice(90,{dur:.32,type:'sawtooth',vol:.08,attack:.002});
      voice(880,{dur:.06,type:'square',vol:.05,delay:.03});
      voice(1400,{dur:.04,type:'square',vol:.03,delay:.05});
    },

    lab(){ // timbre "científico", cristalino
      voice(N.E4,{dur:.15,type:'sine',vol:.055});
      voice(N.A4,{dur:.18,type:'sine',vol:.055,delay:.1});
      voice(N.D5,{dur:.24,type:'sine',vol:.06,delay:.21,release:.35});
    },

    boss(){ // grave e imponente
      voice(73.4,{dur:.55,type:'sawtooth',vol:.09,attack:.01});
      voice(110,{dur:.5,type:'triangle',vol:.06,delay:.08});
      noiseBurst(.4,.05,150,'lowpass');
    },

    quiz(){voice(N.A4,{dur:.09,type:'sine',vol:.05});voice(N.D5,{dur:.13,type:'sine',vol:.05,delay:.07})},

    levelup(){ // insignia nueva — más grande que reward
      chord([N.C4,N.E4,N.G4],{dur:.18,type:'triangle',vol:.08});
      chord([N.C5,N.E5,N.G5],{dur:.5,type:'sine',vol:.1,delay:.22,release:.7});
      voice(N.C5*2,{dur:.4,type:'sine',vol:.04,delay:.3,release:.6});
    }
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
