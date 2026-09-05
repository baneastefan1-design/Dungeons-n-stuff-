(() => {
  const canvas = document.querySelector('#game'), ctx = canvas.getContext('2d'), menu = document.querySelector('#menu'), status = document.querySelector('#status');
  const menuTitle = document.querySelector('#menu-title'), menuCopy = document.querySelector('#menu-copy'), dismissResult = document.querySelector('#result-dismiss'), nextButton = document.querySelector('#new-game'), soundButton = document.querySelector('#sound-toggle'), assets = {};
  const names = ['hero/idle','hero/walk','dragon/sleeping','dragon/awake','tiles/floor_1','tiles/floor_2','tiles/wall_horizontal','tiles/wall_vertical','portal','treasure_open','scorch','fog'];
  const keys = {ArrowUp:'up',w:'up',W:'up',ArrowDown:'down',s:'down',S:'down',ArrowLeft:'left',a:'left',A:'left',ArrowRight:'right',d:'right',D:'right'};
  let state = null, socket = null, swipe = null, resultTimer = null, lastResult = null, audioContext = null;
  let muted = localStorage.getItem('dungeon-escape-muted') === 'true';
  const load = name => new Promise(resolve => { const img = new Image(); img.src = `/assets/illustrated/${name}.png`; img.onload = () => { assets[name] = img; resolve(); }; img.onerror = resolve; });
  Promise.all(names.map(load)).then(resize);
  function updateSoundButton() { soundButton.textContent = muted ? 'Sound: off' : 'Sound: on'; soundButton.setAttribute('aria-pressed', String(!muted)); }
  function wakeAudio() { if (muted || !(window.AudioContext || window.webkitAudioContext)) return; audioContext ||= new (window.AudioContext || window.webkitAudioContext)(); if (audioContext.state === 'suspended') audioContext.resume(); }
  function playSound(notes, volume = .24) {
    if (muted || !audioContext) return;
    let time = audioContext.currentTime;
    for (const [frequency, duration] of notes) {
      const oscillator = audioContext.createOscillator(), gain = audioContext.createGain();
      oscillator.type = 'sine'; oscillator.frequency.value = frequency; gain.gain.setValueAtTime(0.0001, time); gain.gain.exponentialRampToValueAtTime(volume, time + .012); gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
      oscillator.connect(gain).connect(audioContext.destination); oscillator.start(time); oscillator.stop(time + duration + .02); time += duration;
    }
  }
  const soundRecipes = { step: [[[180,.045]],.16], bump: [[[90,.11]],.24], treasure: [[[659,.08],[784,.09],[1047,.16]],.26], growl: [[[150,.13],[105,.17],[78,.18]],.30], win: [[[523,.10],[659,.10],[784,.18]],.28], lose: [[[220,.12],[165,.14],[110,.24]],.28] };
  function cue(name) { const [notes, volume] = soundRecipes[name]; playSound(notes, volume); }
  function playFeedback(previous, next) {
    if (!previous) return;
    if (previous.status === 'playing' && next.status !== 'playing') { cue(next.status === 'eaten' ? 'lose' : 'win'); return; }
    if (previous.status !== 'playing' || next.status !== 'playing') return;
    if (previous.player[0] === next.player[0] && previous.player[1] === next.player[1]) { cue('bump'); return; }
    cue('step'); if (!previous.has_treasure && next.has_treasure) cue('treasure'); if (!previous.dragon_awake && next.dragon_awake) cue('growl');
  }
  updateSoundButton();
  function send(value) { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(value)); }
  function resultCopy(kind) {
    const nextSize = Math.min(16, state.grid_size + 1);
    if (kind === 'won') return ['Treasure escape!', `Your streak is ${state.streak}. The next dungeon grows from ${state.grid_size}×${state.grid_size} to ${nextSize}×${nextSize}. Choose a mode to continue.`];
    if (kind === 'escaped') return ['You escaped safely.', `You returned without the treasure, so your streak and next dungeon stay at ${state.grid_size}×${state.grid_size}. Choose a mode to continue.`];
    return ['The dragon got you.', 'Your streak resets, so the next dungeon returns to 8×8. Inspect this dungeon or choose a mode to try again.'];
  }
  function showResult() { if (!lastResult) return; menuTitle.textContent = lastResult.title; menuCopy.textContent = lastResult.copy; dismissResult.hidden = false; menu.hidden = false; nextButton.textContent = 'Results & next dungeon'; }
  function showMainMenu() { lastResult = null; dismissResult.hidden = true; menuTitle.textContent = 'Dungeon Escape'; menuCopy.textContent = 'Find the treasure, evade the sleeping dragon, and return to the portal.'; menu.hidden = false; nextButton.textContent = 'Main menu'; }
  function connect() { if (socket?.readyState === WebSocket.OPEN) return; socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`); socket.onmessage = event => { const previous = state; state = JSON.parse(event.data); playFeedback(previous, state); status.textContent = state.hint; status.hidden = state.status === 'playing'; if (state.status !== 'playing' && !resultTimer) { const [title, copy] = resultCopy(state.status); lastResult = {title, copy}; resultTimer = setTimeout(() => { showResult(); resultTimer = null; }, 2000); } draw(); }; socket.onclose = () => { status.hidden = false; status.textContent = 'Connection lost. Reload to reconnect.'; }; }
  function start(difficulty) { wakeAudio(); clearTimeout(resultTimer); resultTimer = null; lastResult = null; state = null; dismissResult.hidden = true; nextButton.textContent = 'Main menu'; connect(); const begin = () => send({action:'start', difficulty}); if (socket.readyState === WebSocket.OPEN) begin(); else socket.addEventListener('open', begin, {once:true}); menu.hidden = true; }
  function move(direction) { if (state?.status === 'playing') { wakeAudio(); send({action:'move', direction}); } }
  function has(items, x, y) { return items.some(item => item[0] === x && item[1] === y); }
  function sprite(name, x, y, size) { if (assets[name]) ctx.drawImage(assets[name], x, y, size, size); }
  function resize() { const box = canvas.getBoundingClientRect(), ratio = Math.min(devicePixelRatio || 1, 2); canvas.width = box.width * ratio; canvas.height = box.height * ratio; ctx.setTransform(ratio,0,0,ratio,0,0); draw(); }
  function draw() {
    const width = canvas.clientWidth, height = canvas.clientHeight; ctx.clearRect(0,0,width,height); ctx.fillStyle = '#111827'; ctx.fillRect(0,0,width,height); if (!state) return;
    const pad = Math.min(width,height)*.025, hud = Math.max(68,height*.1), tile = Math.min((width-pad*2)/state.grid_size,(height-pad*2-hud)/state.grid_size), board = tile*state.grid_size, left=(width-board)/2, top=pad+hud;
    ctx.fillStyle='#f6f4e8'; ctx.font=`700 ${Math.max(14,tile*.31)}px system-ui`; ctx.textAlign='left'; ctx.fillText(`Moves ${state.moves}   ${state.hard_mode ? 'Hard' : 'Normal'}${state.has_treasure ? '   Treasure ✓' : ''}`,left,top-Math.max(30,tile*.48));
    if (state.hint === 'The air feels warm nearby…') { ctx.fillStyle='#ffd34d'; ctx.font=`700 ${Math.max(13,tile*.24)}px system-ui`; ctx.fillText('⚠ The air feels warm nearby…',left,top-10); }
    for(let y=0;y<state.grid_size;y++) for(let x=0;x<state.grid_size;x++) sprite(`tiles/floor_${(x+y)%2+1}`,left+x*tile,top+y*tile,tile);
    for(const [x,y] of state.scorched) sprite('scorch',left+x*tile,top+y*tile,tile);
    sprite('portal',left+state.start[0]*tile,top+state.start[1]*tile,tile);
    const treasureVisible = state.status !== 'playing' || has(state.visited,...state.treasure) || Math.max(Math.abs(state.treasure[0]-state.player[0]),Math.abs(state.treasure[1]-state.player[1])) <= 2;
    if (treasureVisible && !state.has_treasure) sprite('treasure_open',left+state.treasure[0]*tile,top+state.treasure[1]*tile,tile);
    if (state.dragon_awake || state.status !== 'playing') sprite(state.dragon_awake?'dragon/awake':'dragon/sleeping',left+state.dragon[0]*tile,top+state.dragon[1]*tile,tile);
    for(let y=0;y<state.grid_size;y++) for(let x=0;x<state.grid_size;x++) { const seen=has(state.visited,x,y)||Math.max(Math.abs(x-state.player[0]),Math.abs(y-state.player[1]))<=2||state.status!=='playing'; if(!seen&&!(state.dragon_awake&&x===state.dragon[0]&&y===state.dragon[1])) sprite('fog',left+x*tile,top+y*tile,tile); }
    const thick=Math.max(5,tile*.18); for(const [x,y] of state.horizontal_walls) if(assets['tiles/wall_horizontal']) ctx.drawImage(assets['tiles/wall_horizontal'],left+x*tile,top+(y+1)*tile-thick/2,tile,thick); for(const [x,y] of state.vertical_walls) if(assets['tiles/wall_vertical']) ctx.drawImage(assets['tiles/wall_vertical'],left+(x+1)*tile-thick/2,top+y*tile,thick,tile);
    if (state.has_treasure) { const x=left+(state.treasure[0]+.5)*tile, y=top+(state.treasure[1]+.5)*tile, size=tile*.18; ctx.strokeStyle='#ef5965'; ctx.lineWidth=Math.max(3,tile*.07); ctx.beginPath(); ctx.moveTo(x-size,y-size); ctx.lineTo(x+size,y+size); ctx.moveTo(x+size,y-size); ctx.lineTo(x-size,y+size); ctx.stroke(); }
    sprite(state.moves%2?'hero/walk':'hero/idle',left+state.player[0]*tile,top+state.player[1]*tile,tile);
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click',()=>start(button.dataset.mode)));
  document.querySelectorAll('[data-direction]').forEach(button => button.addEventListener('click',()=>move(button.dataset.direction)));
  nextButton.addEventListener('click',()=>{ if (lastResult) showResult(); else showMainMenu(); });
  dismissResult.addEventListener('click',()=>{ menu.hidden=true; });
  soundButton.addEventListener('click',()=>{ muted = !muted; localStorage.setItem('dungeon-escape-muted', String(muted)); updateSoundButton(); if (!muted) wakeAudio(); });
  addEventListener('keydown',event=>{const direction=keys[event.key];if(direction){event.preventDefault();move(direction);}}); canvas.addEventListener('pointerdown',event=>{swipe=[event.clientX,event.clientY];}); canvas.addEventListener('pointerup',event=>{if(!swipe)return;const dx=event.clientX-swipe[0],dy=event.clientY-swipe[1];swipe=null;if(Math.max(Math.abs(dx),Math.abs(dy))>25)move(Math.abs(dx)>Math.abs(dy)?(dx>0?'right':'left'):(dy>0?'down':'up'));}); new ResizeObserver(resize).observe(canvas);
})();
