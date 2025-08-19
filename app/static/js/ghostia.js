(function(){
  class GhostIA extends HTMLElement {
    constructor(){
      super();
      this.attachShadow({mode:'open'});
      this.shadowRoot.innerHTML = `
        <style>
          :host{ position: fixed; right: 16px; bottom: 16px; z-index: 9999; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial }
          :host([layout="page"]) { position: static; display:block; }
          .launcher{ position:absolute; right:0; bottom:0; width:56px; height:56px; border-radius:50%; border:0; background:#111827; color:#e5e7eb; display:grid; place-items:center; cursor:pointer; box-shadow:0 10px 25px rgba(0,0,0,.25) }
          .launcher:hover{ filter:brightness(1.08) }
          .panel{ position:absolute; right:0; bottom:72px; width:min(380px,92vw); height:min(560px,78vh); background:#0a0a0a; color:#e6e6e6; border:1px solid #0f172a; border-radius:14px; box-shadow:0 18px 60px rgba(0,0,0,.55); display:none; grid-template-rows:auto 1fr auto; overflow:hidden }
          :host([layout="page"]) .panel{ position:relative; right:auto; bottom:auto; width:100%; height:auto; border-radius:0; box-shadow:none; margin:0; background:transparent; border:0; display:none; grid-template-rows:auto auto; }
          .panel.open{ display:grid }
          :host([layout="page"]) .panel.open{ display:grid }
          .header{ display:flex; align-items:center; justify-content:space-between; padding:10px 12px; background:linear-gradient(180deg,#0f172a,#0b1324); border-bottom:1px solid #0f172a }
          :host([layout="page"]) .header{ display:none }
          .title{ font-weight:800; display:flex; align-items:center; gap:8px }
          .dot{ width:8px; height:8px; border-radius:50%; background:#22c55e; box-shadow:0 0 10px #22c55e99 }
          .actions{ display:flex; gap:6px }
          .close{ width:32px; height:32px; border-radius:8px; border:1px solid #111827; background:#0b0b0b; color:#e6e6e6; cursor:pointer }
          .messages{ overflow:auto; padding:12px; display:flex; flex-direction:column; gap:14px; scroll-behavior:smooth }
          :host([layout="page"]) .messages{ width:min(920px,96vw); margin: 0 auto; max-height:none }
          .msg{ max-width:85%; padding:10px 12px; border-radius:12px; line-height:1.35; font-size:14px; white-space:pre-wrap; word-wrap:break-word }
          .msg.user{ align-self:flex-end; background:#1e3a8a; color:#eaf2ff; box-shadow:0 6px 18px rgba(30,58,138,.28) }
          .msg.bot{ align-self:flex-start; background:#111827; color:#e6e6e6; border:1px solid #0b1220 }
          .msg.thinking{ position:relative; overflow:hidden; }
          .dots{ display:inline-flex; gap:4px; align-items:center }
          .dots span{ width:6px; height:6px; background:#9aa0a6; border-radius:50%; display:inline-block; opacity:.3; animation:blink 1s infinite }
          .dots span:nth-child(2){ animation-delay:.15s }
          .dots span:nth-child(3){ animation-delay:.3s }
          @keyframes blink{ 0%,100%{ opacity:.2 } 50%{ opacity:1 } }
          .hint{ color:#9aa0a6; font-size:12px; padding:0 12px 8px }
          .composer{ padding:8px; border-top:1px solid #0f172a; display:grid; grid-template-columns:1fr auto auto auto; gap:6px; background:#0a0a0a }
          :host([layout="page"]) .composer{ border-top:0; background:transparent; padding:0; margin: 16px auto 10vh; width:min(920px,96vw); grid-template-columns:1fr auto auto auto; }
          .input{ resize:none; min-height:44px; max-height:160px; padding:12px 14px; border-radius:999px; border:1px solid #111827; background:#0b0b0b; color:#e6e6e6 }
          .btn{ height:44px; padding:0 12px; border-radius:999px; border:1px solid #111827; background:#0b1220; color:#e6e6e6; cursor:pointer }
          .send{ background:#00c2ff; color:#001018; border-color:#00c2ff; font-weight:700 }
          .reset{ background:#0b0b0b; }
          .toggle{ display:inline-flex; align-items:center; gap:6px; background:#0b0b0b; border:1px solid #111827; border-radius:999px; padding:4px 8px; height:32px; color:#e6e6e6 }
          .toggle input{ appearance:none; width:14px; height:14px; border:1px solid #334155 }
          .toggle input:checked{ background:#22c55e; border-color:#22c55e; box-shadow:0 0 10px #22c55e55 }

          
          .hero{ display:none }
          :host([layout="page"]) .hero{ display:grid; place-items:center; padding:8vh 16px 4vh }
          .hero-inner{ width:min(920px,96vw); display:grid; gap:28px }
          .hero-title{ text-align:center; font-size:clamp(28px,4vw,44px); font-weight:800; color:#e6e6e6 }
          .hero-composer{ display:grid; grid-template-columns:1fr auto auto; gap:10px; background:#0b0b0b; border:1px solid #111827; border-radius:999px; padding:10px 12px }
          .hero-input{ width:100%; height:44px; background:transparent; border:0; outline:none; color:#e6e6e6; font-size:16px }
          .hero-btn{ height:40px; width:40px; display:grid; place-items:center; border-radius:999px; border:1px solid #111827; background:#0b1220; color:#e6e6e6; cursor:pointer }
          .hero-send{ background:#00c2ff; color:#001018; border-color:#00c2ff; font-weight:800 }
        </style>
        <button class="launcher" title="Abrir GhostIA" aria-label="Abrir GhostIA">🤖</button>
        <section class="hero" role="region" aria-label="Boas-vindas GhostIA">
          <div class="hero-inner">
            <h1 class="hero-title">Olá! Em que a GhostIA pode te ajudar hoje?</h1>
            <div class="hero-composer">
              <input class="hero-input" placeholder="Pergunte alguma coisa" />
              <button class="hero-btn hero-mic" title="Falar">🎤</button>
              <button class="hero-btn hero-send" title="Enviar">➤</button>
            </div>
          </div>
        </section>
        <section class="panel" role="dialog" aria-live="polite" aria-label="Assistente GhostIA">
          <header class="header">
            <div class="title"><span class="dot"></span> <span>GhostIA</span></div>
            <div class="actions">
              <label class="toggle"><input type="checkbox" class="tts" /> Voz</label>
              <button class="close" title="Fechar" aria-label="Fechar">✕</button>
            </div>
          </header>
          <div class="messages"></div>
          <div class="hint">Pergunte sobre estoque, status e localização.</div>
          <div class="composer">
            <textarea class="input" rows="1" placeholder="Digite sua pergunta..."></textarea>
            <button class="btn mic" title="Falar">🎤</button>
            <button class="btn reset" title="Resetar chat" aria-label="Resetar">↺</button>
            <button class="btn send" title="Enviar">Enviar</button>
          </div>
        </section>
      `;
      this.state = { open:false, tts:false, recognizing:false, started:false };
    }

    connectedCallback(){
      this.$ = (s)=> this.shadowRoot.querySelector(s);
      this.launcher = this.$('.launcher');
      this.hero = this.$('.hero');
      this.heroInput = this.$('.hero-input');
      this.heroSend = this.$('.hero-send');
      this.heroMic = this.$('.hero-mic');
      this.panel = this.$('.panel');
      this.messages = this.$('.messages');
      this.input = this.$('.input');
      this.btnSend = this.$('.send');
      this.btnMic = this.$('.mic');
      this.btnReset = this.$('.reset');
      this.btnClose = this.$('.close');
      this.ttsToggle = this.$('.tts');
      this._bind();
      if (this.getAttribute('layout') !== 'page') this._welcome();
      this._initSpeech();
      if (this.getAttribute('layout') === 'page') {
        this.launcher.style.display = 'none';
        this.panel.classList.remove('open');
        this.state.open = false;
      } else if (this.hasAttribute('open')) {
        this.toggle(true);
      }
    }

    _bind(){
      this.launcher.addEventListener('click', ()=> this.toggle(true));
      this.btnClose.addEventListener('click', ()=> this.toggle(false));
      this.btnSend.addEventListener('click', ()=> this._submit());
      this.btnMic.addEventListener('click', ()=> this._toggleRec());
      this.btnReset.addEventListener('click', ()=> this._reset());
      this.heroSend.addEventListener('click', ()=> this._submitText(this.heroInput.value));
      this.heroInput.addEventListener('keydown', (e)=>{ if(e.key==='Enter'){ e.preventDefault(); this._submitText(this.heroInput.value); }});
      this.heroMic.addEventListener('click', ()=> this._toggleRec());
      this.ttsToggle.addEventListener('change', (e)=> this.state.tts = !!e.target.checked);
      this.input.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); this._submit(); }});
    }

    toggle(open){
      this.state.open = open ?? !this.state.open;
      this.panel.classList.toggle('open', this.state.open);
      this.launcher.style.display = this.state.open ? 'none' : 'grid';
      if(this.state.open) setTimeout(()=> this._scroll(), 0);
    }

    _welcome(){ this._append('bot', 'Olá! Sou a GhostIA. Como posso ajudar? (respostas simuladas)'); }

    _append(role, text){
      const el = document.createElement('div');
      el.className = `msg ${role}`;
      el.textContent = text;
      this.messages.appendChild(el);
      this._scroll();
      if(role==='bot' && this.state.tts) this._speak(text);
    }
    _scroll(){ this.messages.scrollTop = this.messages.scrollHeight + 1000; }

    async _submit(){
      const q = (this.input.value||'').trim();
      return this._submitText(q);
    }

    async _submitText(q){
      if(!q) return;
      if(this.getAttribute('layout') === 'page' && !this.state.started){
        this.state.started = true;
        if(this.hero) this.hero.style.display = 'none';
        this.panel.classList.add('open');
        try{ this.dispatchEvent(new CustomEvent('ghostia:start', { bubbles:true })); }catch(_){}
      }
      this._append('user', q);
      this.input.value='';
      if(this.heroInput) this.heroInput.value='';
      try{
        const thinking = document.createElement('div');
        thinking.className = 'msg bot thinking';
        thinking.innerHTML = '<span class="dots"><span></span><span></span><span></span></span>';
        this.messages.appendChild(thinking); this._scroll();
        const wait = (ms)=> new Promise(r=> setTimeout(r, ms));
        await wait(400);
        let rs = await fetch('/ai/solve?q='+encodeURIComponent(q));
        if(!rs.ok){ rs = await fetch('/ai/solve', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ q }) }); }
        if(rs.ok){
          const dj = await rs.json();
          thinking.remove();
          await this._typeBot(dj.text || '');
          return;
        }
        let r1 = await fetch('/ai/chat?q='+encodeURIComponent(q));
        if(!r1.ok){ r1 = await fetch('/ai/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ q }) }); }
        if(r1.ok){ const d = await r1.json(); thinking.remove(); await this._typeBot(d.text || ''); return; }
        const t2 = await this._fakeAnswer(q);
        thinking.remove();
        await this._typeBot(t2);
      }catch(_){
        const t = await this._fakeAnswer(q);
        await this._typeBot(t);
      }
    }

    async _typeBot(fullText){
      const el = document.createElement('div');
      el.className = 'msg bot';
      this.messages.appendChild(el);
      this._scroll();
      const start = Date.now();
      const minMs = 4000;
      const typeDelay = Math.max(10, Math.floor((minMs - 800) / Math.max(fullText.length, 20)));
      for(let i=0;i<fullText.length;i++){
        el.textContent = fullText.slice(0, i+1);
        this._scroll();
        await new Promise(r=> setTimeout(r, typeDelay));
      }
      const spent = Date.now() - start;
      if(spent < minMs){ await new Promise(r=> setTimeout(r, minMs - spent)); }
      if(this.state.tts) this._speak(fullText);
    }

    _reset(){
      try{ if(this.state.recognizing && this.rec) this.rec.stop(); }catch(_){ }
      this.messages.innerHTML = '';
      this.input.value = '';
      if(this.heroInput) this.heroInput.value = '';
      if(this.getAttribute('layout') === 'page'){
        this.state.started = false;
        if(this.hero) this.hero.style.display = 'grid';
        this.panel.classList.remove('open');
      } else {
        this._welcome();
      }
      try{ this.dispatchEvent(new CustomEvent('ghostia:reset', { bubbles:true })); }catch(_){ }
    }

    async _fakeAnswer(q){
      const t = q.toLowerCase();
      if(/total|dispon[ií]vel|resumo|estoque/.test(t)){
        return 'Resumo (simulado) — Total: 35.943 • Disponíveis: 10.645 • Em uso: 24.716 • Em manutenção: 582 • Aguardando: 1.350';
      }
      const code = (t.match(/\b([a-z]{2,6}\d{3,})\b/i)||[])[1];
      if(/status|situa[cç][aã]o/.test(t) && code){
        return `Status (simulado) de ${code.toUpperCase()}: locado • Tipo: cama • Local: Rio de Janeiro`;
      }
      if(/onde|local|localiza/.test(t) && code){
        return `Localização (simulada) de ${code.toUpperCase()}: Estoque AL • Cidade RJ • Coordenadas -22.912,-43.230`;
      }
      if(/manuten[cç][aã]o|aguardando/.test(t)){
        return 'Manutenção (simulado) — Em manutenção: 582 • Aguardando: 1.350';
      }
      if(/tipo|colch[aã]o|cama|cadeira|muletas|andador/.test(t)){
        return 'Por tipo (simulado) — Cama: 12.908 • Cadeira hig.: 5.699 • Cadeira rodas: 5.097 • Muletas: 232 • Andador: 442 • CPNEU: 2.035';
      }
      return 'Não tenho certeza (simulado). Tente: "Quantos disponíveis?" ou "Status do item CAM00123"';
    }

    _initSpeech(){
      const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if(!Rec){ this.btnMic.disabled = true; this.btnMic.title = 'Reconhecimento de voz indisponível'; return; }
      const rec = this.rec = new Rec();
      rec.lang = 'pt-BR'; rec.interimResults = false; rec.maxAlternatives = 1;
      rec.onstart = ()=>{ this.state.recognizing=true; this.btnMic.classList.add('active'); };
      rec.onend = ()=>{ this.state.recognizing=false; this.btnMic.classList.remove('active'); };
      rec.onerror = ()=>{ this.state.recognizing=false; this.btnMic.classList.remove('active'); };
      rec.onresult = (e)=>{ try{ const txt = (e.results?.[0]?.[0]?.transcript||'').trim(); if(!txt) return; const target = (this.getAttribute('layout')==='page' && !this.state.started) ? this.heroInput : this.input; target.value = txt; if(target===this.heroInput) this._submitText(txt); else this._submit(); }catch(_){} };
    }
    _toggleRec(){ if(!this.rec) return; if(this.state.recognizing){ try{ this.rec.stop(); }catch(_){} } else { try{ this.rec.start(); }catch(_){} } }
    _speak(text){ try{ const u = new SpeechSynthesisUtterance(text); u.lang='pt-BR'; speechSynthesis.cancel(); speechSynthesis.speak(u);}catch(_){} }
  }
  customElements.define('ghost-ia', GhostIA);
})();


