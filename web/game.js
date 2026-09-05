(() => {
  const canvas = document.querySelector('#game'), ctx = canvas.getContext('2d'), menu = document.querySelector('#menu'), status = document.querySelector('#status');
  const menuTitle = document.querySelector('#menu-title'), menuCopy = document.querySelector('#menu-copy'), assets = {};
  const names = ['hero/idle','hero/walk','dragon/sleeping','dragon/awake','tiles/floor_1','tiles/floor_2','tiles/wall_horizontal','tiles/wall_vertical','portal','treasure_open','scorch','fog'];
  const keys = {ArrowUp:'up',w:'up',W:'up',ArrowDown:'down',s:'down',S:'down',ArrowLeft:'left',a:'left',A:'left',ArrowRight:'right',d:'right',D:'right'};
  let state = null, socket = null, swipe = null, resultTimer = null;
  const load = name => new Promise(resolve => { const img = new Image(); img.src = `/assets/illustrated/${name}.png`; img.onload = () => { assets[name] = img; resolve(); }; img.onerror = resolve; });
  Promise.all(names.map(load)).then(resize);
  function send(value) { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(value)); }
  function resultCopy(kind) {
    if (kind === 'won') return ['You escaped with the treasure!', `A complete escape in ${state.moves} moves. Choose a difficulty for a new dungeon.`];
    if (kind === 'escaped') return ['You escaped safely.', 'The dragon woke, but you made it back to the portal. Choose a difficulty for a new dungeon.'];
    return ['The dragon got you.', 'The dungeon is different every time. Choose a difficulty and try again.'];
  }
  function connect() { if (socket?.readyState === WebSocket.OPEN) return; socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`); socket.onmessage = event => { state = JSON.parse(event.data); status.textContent = state.hint; status.hidden = state.status === 'playing'; if (state.status !== 'playing' && !resultTimer) { const [title, copy] = resultCopy(state.status); resultTimer = setTimeout(() => { menuTitle.textContent = title; menuCopy.textContent = copy; menu.hidden = false; resultTimer = null; }, 2000); } draw(); }; socket.onclose = () => { status.hidden = false; status.textContent = 'Connection lost. Reload to reconnect.'; }; }
  function start(difficulty) { clearTimeout(resultTimer); resultTimer = null; connect(); const begin = () => send({action:'start', difficulty}); if (socket.readyState === WebSocket.OPEN) begin(); else socket.addEventListener('open', begin, {once:true}); menu.hidden = true; }
  function move(direction) { if (state?.status === 'playing') send({action:'move', direction}); }
  function has(items, x, y) { return items.some(item => item[0] === x && item[1] === y); }
  function sprite(name, x, y, size) { if (assets[name]) ctx.drawImage(assets[name], x, y, size, size); }
  function resize() { const box = canvas.getBoundingClientRect(), ratio = Math.min(devicePixelRatio || 1, 2); canvas.width = box.width * ratio; canvas.height = box.height * ratio; ctx.setTransform(ratio,0,0,ratio,0,0); draw(); }
  function draw() {
    const width = canvas.clientWidth, height = canvas.clientHeight; ctx.clearRect(0,0,width,height); ctx.fillStyle = '#111827'; ctx.fillRect(0,0,width,height); if (!state) return;
    const pad = Math.min(width,height)*.025, hud = Math.max(38,height*.07), tile = Math.min((width-pad*2)/state.grid_size,(height-pad*2-hud)/state.grid_size), board = tile*state.grid_size, left=(width-board)/2, top=pad+hud;
    ctx.fillStyle='#f6f4e8'; ctx.font=`700 ${Math.max(14,tile*.31)}px system-ui`; ctx.textAlign='left'; ctx.fillText(`Moves ${state.moves}   ${state.hard_mode ? 'Hard' : 'Normal'}`,left,top-14);
    if (state.hint === 'The air feels warm nearby…') { ctx.fillStyle='#ffd34d'; ctx.textAlign='right'; ctx.fillText('⚠ The air feels warm nearby…',left+board,top-14); }
    for(let y=0;y<state.grid_size;y++) for(let x=0;x<state.grid_size;x++) sprite(`tiles/floor_${(x+y)%2+1}`,left+x*tile,top+y*tile,tile);
    for(const [x,y] of state.scorched) sprite('scorch',left+x*tile,top+y*tile,tile);
    sprite('portal',left+state.start[0]*tile,top+state.start[1]*tile,tile);
    if ((state.status !== 'playing' || has(state.visited,...state.treasure)) && !state.has_treasure) sprite('treasure_open',left+state.treasure[0]*tile,top+state.treasure[1]*tile,tile);
    if (state.dragon_awake || state.status !== 'playing') sprite(state.dragon_awake?'dragon/awake':'dragon/sleeping',left+state.dragon[0]*tile,top+state.dragon[1]*tile,tile);
    for(let y=0;y<state.grid_size;y++) for(let x=0;x<state.grid_size;x++) { const seen=has(state.visited,x,y)||Math.max(Math.abs(x-state.player[0]),Math.abs(y-state.player[1]))<=2||state.status!=='playing'; if(!seen&&!(state.dragon_awake&&x===state.dragon[0]&&y===state.dragon[1])) sprite('fog',left+x*tile,top+y*tile,tile); }
    const thick=Math.max(5,tile*.18); for(const [x,y] of state.horizontal_walls) if(assets['tiles/wall_horizontal']) ctx.drawImage(assets['tiles/wall_horizontal'],left+x*tile,top+(y+1)*tile-thick/2,tile,thick); for(const [x,y] of state.vertical_walls) if(assets['tiles/wall_vertical']) ctx.drawImage(assets['tiles/wall_vertical'],left+(x+1)*tile-thick/2,top+y*tile,thick,tile);
    sprite(state.moves%2?'hero/walk':'hero/idle',left+state.player[0]*tile,top+state.player[1]*tile,tile);
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click',()=>start(button.dataset.mode)));
  document.querySelectorAll('[data-direction]').forEach(button => button.addEventListener('click',()=>move(button.dataset.direction)));
  document.querySelector('#new-game').addEventListener('click',()=>{menuTitle.textContent='Dungeon Escape';menuCopy.textContent='Find the treasure, evade the sleeping dragon, and return to the portal.';menu.hidden=false;});
  addEventListener('keydown',event=>{const direction=keys[event.key];if(direction){event.preventDefault();move(direction);}}); canvas.addEventListener('pointerdown',event=>{swipe=[event.clientX,event.clientY];}); canvas.addEventListener('pointerup',event=>{if(!swipe)return;const dx=event.clientX-swipe[0],dy=event.clientY-swipe[1];swipe=null;if(Math.max(Math.abs(dx),Math.abs(dy))>25)move(Math.abs(dx)>Math.abs(dy)?(dx>0?'right':'left'):(dy>0?'down':'up'));}); new ResizeObserver(resize).observe(canvas);
})();
