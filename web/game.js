(() => {
  const canvas = document.querySelector('#game');
  const context = canvas.getContext('2d');
  const menu = document.querySelector('#menu');
  const menuTitle = document.querySelector('#menu-title');
  const menuCopy = document.querySelector('#menu-copy');
  const status = document.querySelector('#status');
  const directions = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
  const keyDirections = { ArrowUp: 'up', w: 'up', W: 'up', ArrowDown: 'down', s: 'down', S: 'down', ArrowLeft: 'left', a: 'left', A: 'left', ArrowRight: 'right', d: 'right', D: 'right' };
  const scores = JSON.parse(localStorage.getItem('dungeon-escape-scores') || '{"wins":0,"best":null}');
  let state = null;
  let swipeStart = null;

  function shuffle(items) { return items.sort(() => Math.random() - .5); }
  function cellKey(x, y) { return `${x},${y}`; }
  function same(a, b) { return a.x === b.x && a.y === b.y; }
  function resize() {
    const rect = canvas.getBoundingClientRect(); const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(rect.width * ratio); canvas.height = Math.round(rect.height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0); draw();
  }
  function makeMaze(size) {
    const cells = Array.from({ length: size }, () => Array.from({ length: size }, () => ({ n: true, e: true, s: true, w: true })));
    const visited = new Set([cellKey(0, 0)]); const stack = [{ x: 0, y: 0 }];
    const options = [{ dx: 0, dy: -1, wall: 'n', opposite: 's' }, { dx: 1, dy: 0, wall: 'e', opposite: 'w' }, { dx: 0, dy: 1, wall: 's', opposite: 'n' }, { dx: -1, dy: 0, wall: 'w', opposite: 'e' }];
    while (stack.length) {
      const current = stack.at(-1); const nexts = shuffle(options.filter(o => current.x + o.dx >= 0 && current.x + o.dx < size && current.y + o.dy >= 0 && current.y + o.dy < size && !visited.has(cellKey(current.x + o.dx, current.y + o.dy))));
      if (!nexts.length) { stack.pop(); continue; }
      const option = nexts[0], next = { x: current.x + option.dx, y: current.y + option.dy };
      cells[current.y][current.x][option.wall] = false; cells[next.y][next.x][option.opposite] = false;
      visited.add(cellKey(next.x, next.y)); stack.push(next);
    }
    return cells;
  }
  function start(mode) {
    const size = mode === 'hard' ? 10 : 9;
    state = { size, cells: makeMaze(size), player: { x: 0, y: 0 }, dragon: { x: size - 1, y: 0 }, treasure: { x: size - 1, y: size - 1 }, mode, moves: 0, awake: false, over: false, visited: new Set([cellKey(0, 0)]) };
    menu.hidden = true; setStatus('Find the gold, then return to the blue portal.'); resize();
  }
  function setStatus(text) { status.textContent = `${text}  Wins: ${scores.wins}${scores.best === null ? '' : ` · Best: ${scores.best} moves`}`; }
  function allowed(position, direction) {
    const [dx, dy] = directions[direction]; const next = { x: position.x + dx, y: position.y + dy };
    if (next.x < 0 || next.y < 0 || next.x >= state.size || next.y >= state.size) return null;
    const wall = { up: 'n', down: 's', left: 'w', right: 'e' }[direction]; return state.cells[position.y][position.x][wall] ? null : next;
  }
  function neighbors(position) { return Object.keys(directions).map(direction => allowed(position, direction)).filter(Boolean); }
  function shortestStep(from, target) {
    const queue = [from], previous = new Map([[cellKey(from.x, from.y), null]]);
    for (let index = 0; index < queue.length; index++) {
      const current = queue[index]; if (same(current, target)) break;
      for (const next of neighbors(current)) { const key = cellKey(next.x, next.y); if (!previous.has(key)) { previous.set(key, current); queue.push(next); } }
    }
    const targetKey = cellKey(target.x, target.y); if (!previous.has(targetKey)) return from;
    let cursor = target; while (previous.get(cellKey(cursor.x, cursor.y)) && !same(previous.get(cellKey(cursor.x, cursor.y)), from)) cursor = previous.get(cellKey(cursor.x, cursor.y));
    return cursor;
  }
  function finish(kind) {
    state.over = true; menu.hidden = false;
    if (kind === 'won') { scores.wins++; scores.best = scores.best === null ? state.moves : Math.min(scores.best, state.moves); localStorage.setItem('dungeon-escape-scores', JSON.stringify(scores)); menuTitle.textContent = 'You escaped!'; menuCopy.textContent = `Treasure secured in ${state.moves} moves. Choose a new dungeon when you are ready.`; setStatus('A legendary escape.'); }
    else { menuTitle.textContent = 'The dragon got you.'; menuCopy.textContent = 'The maze changes every run. Try a new route—or reduce the difficulty.'; setStatus('The dragon guards its treasure well.'); }
    draw();
  }
  function move(direction) {
    if (!state || state.over) return;
    const next = allowed(state.player, direction); if (!next) { setStatus('A solid stone wall blocks the way.'); return; }
    state.player = next; state.moves++; state.visited.add(cellKey(next.x, next.y));
    if (same(next, state.treasure) && !state.hasTreasure) { state.hasTreasure = true; setStatus('Treasure found! Return to the portal. The dragon wakes…'); }
    if (state.hasTreasure && same(next, { x: 0, y: 0 })) { finish('won'); return; }
    const distance = Math.abs(state.player.x - state.dragon.x) + Math.abs(state.player.y - state.dragon.y);
    if (state.hasTreasure || distance < 6) state.awake = true;
    const cadence = state.mode === 'hard' ? 1 : state.mode === 'normal' ? 2 : 3;
    if (state.awake && state.moves % cadence === 0) state.dragon = shortestStep(state.dragon, state.player);
    if (same(state.player, state.dragon)) { finish('eaten'); return; }
    setStatus(state.awake ? 'The dragon is hunting. Keep moving!' : 'The dungeon is quiet… for now.'); draw();
  }
  function drawToken(x, y, size, type) {
    const cx = x + size / 2, cy = y + size / 2;
    if (type === 'portal') { context.strokeStyle = '#52b9ff'; context.lineWidth = size * .11; context.beginPath(); context.arc(cx, cy, size * .27, 0, Math.PI * 2); context.stroke(); context.strokeStyle = '#a9e6ff'; context.lineWidth = size * .04; context.stroke(); }
    if (type === 'gold') { context.fillStyle = '#f5be3f'; context.fillRect(cx - size * .22, cy - size * .13, size * .44, size * .27); context.fillStyle = '#ffe08a'; context.fillRect(cx - size * .16, cy - size * .24, size * .32, size * .12); }
    if (type === 'hero') { context.fillStyle = '#6fcbff'; context.beginPath(); context.arc(cx, cy - size * .09, size * .14, 0, Math.PI * 2); context.fill(); context.fillStyle = '#d8f2ff'; context.fillRect(cx - size * .16, cy + size * .04, size * .32, size * .22); }
    if (type === 'dragon') { context.fillStyle = '#e15b5b'; context.beginPath(); context.arc(cx, cy, size * .27, 0, Math.PI * 2); context.fill(); context.fillStyle = '#ffcf61'; context.fillRect(cx - size * .11, cy - size * .06, size * .06, size * .06); context.fillRect(cx + size * .05, cy - size * .06, size * .06, size * .06); }
  }
  function draw() {
    if (!state) return; const width = canvas.clientWidth, height = canvas.clientHeight, pad = Math.min(width, height) * .045; const board = Math.min(width, height) - pad * 2; const tile = board / state.size;
    context.clearRect(0, 0, width, height); context.fillStyle = '#111a2d'; context.fillRect(0, 0, width, height);
    for (let y = 0; y < state.size; y++) for (let x = 0; x < state.size; x++) {
      const px = pad + x * tile, py = pad + y * tile, seen = state.visited.has(cellKey(x, y)) || state.over;
      context.fillStyle = seen ? ((x + y) % 2 ? '#293a58' : '#253550') : '#18243a'; context.fillRect(px, py, tile, tile);
      const c = state.cells[y][x]; context.strokeStyle = '#91a4c7'; context.lineWidth = Math.max(2, tile * .055); context.beginPath(); if (c.n) { context.moveTo(px, py); context.lineTo(px + tile, py); } if (c.w) { context.moveTo(px, py); context.lineTo(px, py + tile); } if (c.e) { context.moveTo(px + tile, py); context.lineTo(px + tile, py + tile); } if (c.s) { context.moveTo(px, py + tile); context.lineTo(px + tile, py + tile); } context.stroke();
    }
    drawToken(pad, pad, tile, 'portal'); if (!state.hasTreasure) drawToken(pad + state.treasure.x * tile, pad + state.treasure.y * tile, tile, 'gold');
    if (state.awake || state.over) drawToken(pad + state.dragon.x * tile, pad + state.dragon.y * tile, tile, 'dragon'); drawToken(pad + state.player.x * tile, pad + state.player.y * tile, tile, 'hero');
    context.fillStyle = '#f6f4e8'; context.font = `700 ${Math.max(13, tile * .29)}px system-ui`; context.textAlign = 'left'; context.fillText(`Moves: ${state.moves}${state.hasTreasure ? ' · Treasure ✓' : ''}`, pad, height - pad * .35);
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => start(button.dataset.mode)));
  document.querySelectorAll('[data-direction]').forEach(button => button.addEventListener('click', () => move(button.dataset.direction)));
  document.querySelector('#new-game').addEventListener('click', () => { menuTitle.textContent = 'Dungeon Escape'; menuCopy.textContent = 'Find the gold, then return to the portal. The dragon hunts once it wakes.'; menu.hidden = false; });
  window.addEventListener('keydown', event => { const direction = keyDirections[event.key]; if (direction) { event.preventDefault(); move(direction); } });
  canvas.addEventListener('pointerdown', event => { swipeStart = { x: event.clientX, y: event.clientY }; });
  canvas.addEventListener('pointerup', event => { if (!swipeStart) return; const dx = event.clientX - swipeStart.x, dy = event.clientY - swipeStart.y; swipeStart = null; if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return; move(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up')); });
  new ResizeObserver(resize).observe(canvas); window.addEventListener('resize', resize);
})();
