(() => {
  const canvas = document.querySelector("#game"),
    ctx = canvas.getContext("2d"),
    menu = document.querySelector("#menu"),
    status = document.querySelector("#status");
  const menuTitle = document.querySelector("#menu-title"),
    menuCopy = document.querySelector("#menu-copy"),
    dismissResult = document.querySelector("#result-dismiss"),
    nextButton = document.querySelector("#new-game"),
    soundButton = document.querySelector("#sound-toggle"),
    profileButton = document.querySelector("#profile-toggle"),
    usernameInput = document.querySelector("#username"),
    debugLevelField = document.querySelector("#debug-level-field"),
    debugLevelInput = document.querySelector("#debug-level"),
    rules = document.querySelector("#rules"),
    rulesButton = document.querySelector("#rules-toggle"),
    leaderboard = document.querySelector("#leaderboard"),
    leaderboardBody = document.querySelector("#leaderboard-body"),
    assets = {};
  const names = [
    "hero/idle",
    "hero/walk",
    "dragon/sleeping",
    "dragon/awake",
    "tiles/floor_1",
    "tiles/floor_2",
    "tiles/wall_horizontal",
    "tiles/wall_vertical",
    "portal",
    "heart",
    "treasure_open",
    "scorch",
    "fog",
  ];
  const keys = {
    ArrowUp: "up",
    w: "up",
    W: "up",
    ArrowDown: "down",
    s: "down",
    S: "down",
    ArrowLeft: "left",
    a: "left",
    A: "left",
    ArrowRight: "right",
    d: "right",
    D: "right",
  };
  const debugMode = location.pathname.replace(/\/+$/, "") === "/debug";
  const debugLog = (...values) => {
    if (debugMode) console.info("[Dungeon debug]", ...values);
  };
  let state = null,
    socket = null,
    swipe = null,
    resultTimer = null,
    lastResult = null,
    wakeUntil = 0,
    audioContext = null;
  let muted = localStorage.getItem("dungeon-escape-muted") === "true";
  let clientId = localStorage.getItem("dungeon-escape-client-id");
  if (!clientId) {
    clientId = crypto.randomUUID();
    localStorage.setItem("dungeon-escape-client-id", clientId);
  }
  usernameInput.value = localStorage.getItem("dungeon-escape-username") || "";
  // Menus are viewport-level layers, never clipped by the square game board.
  [menu, rules, leaderboard].forEach((overlay) =>
    document.body.append(overlay),
  );
  function setUsernameEditable(editable) {
    usernameInput.readOnly = !editable;
    usernameInput.setAttribute("aria-readonly", String(!editable));
    usernameInput.classList.toggle("locked", !editable);
  }
  setUsernameEditable(!usernameInput.value);
  if (debugMode) {
    debugLevelField.hidden = false;
    document.querySelector(".eyebrow").textContent =
      "DUNGEON ESCAPE · DEBUG MODE";
  }
  const load = (name) =>
    new Promise((resolve) => {
      const img = new Image();
      img.src = `/assets/illustrated/${name}.png`;
      img.onload = () => {
        assets[name] = img;
        resolve();
      };
      img.onerror = resolve;
    });
  Promise.all(names.map(load)).then(resize);
  function updateSoundButton() {
    soundButton.textContent = muted ? "Sound: off" : "Sound: on";
    soundButton.setAttribute("aria-pressed", String(!muted));
  }
  function wakeAudio() {
    if (muted || !(window.AudioContext || window.webkitAudioContext)) return;
    audioContext ||= new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === "suspended") audioContext.resume();
  }
  function playSound(notes, volume = 0.24) {
    if (muted || !audioContext) return;
    let time = audioContext.currentTime;
    for (const [frequency, duration] of notes) {
      const oscillator = audioContext.createOscillator(),
        gain = audioContext.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, time);
      gain.gain.exponentialRampToValueAtTime(volume, time + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
      oscillator.connect(gain).connect(audioContext.destination);
      oscillator.start(time);
      oscillator.stop(time + duration + 0.02);
      time += duration;
    }
  }
  const soundRecipes = {
    step: [[[180, 0.045]], 0.16],
    bump: [[[90, 0.11]], 0.24],
    treasure: [
      [
        [659, 0.08],
        [784, 0.09],
        [1047, 0.16],
      ],
      0.26,
    ],
    growl: [
      [
        [150, 0.13],
        [105, 0.17],
        [78, 0.18],
      ],
      0.3,
    ],
    win: [
      [
        [523, 0.1],
        [659, 0.1],
        [784, 0.18],
      ],
      0.28,
    ],
    lose: [
      [
        [220, 0.12],
        [165, 0.14],
        [110, 0.24],
      ],
      0.28,
    ],
  };
  function cue(name) {
    const [notes, volume] = soundRecipes[name];
    playSound(notes, volume);
  }
  function playFeedback(previous, next) {
    if (!previous) return;
    if (previous.status === "playing" && next.status !== "playing") {
      cue(next.status === "eaten" ? "lose" : "win");
      return;
    }
    if (previous.status !== "playing" || next.status !== "playing") return;
    if (
      previous.player[0] === next.player[0] &&
      previous.player[1] === next.player[1]
    ) {
      cue("bump");
      return;
    }
    cue("step");
    if (!previous.has_treasure && next.has_treasure) cue("treasure");
    if (!previous.dragon_awake && next.dragon_awake) {
      cue("growl");
      wakeUntil = performance.now() + 1450;
      navigator.vibrate?.([70, 45, 160]);
      const animateWake = () => {
        draw();
        if (performance.now() < wakeUntil) requestAnimationFrame(animateWake);
      };
      requestAnimationFrame(animateWake);
    }
  }
  updateSoundButton();
  function send(value) {
    if (socket?.readyState === WebSocket.OPEN) {
      debugLog("send", value);
      socket.send(JSON.stringify(value));
    }
  }
  function resultCopy(kind) {
    const heartNote = state.heart_banked
      ? ` You also delivered a heart, so the next run begins with ${state.hearts}/3 hearts.`
      : "";
    if (kind === "won" && state.level < 6)
      return [
        "Treasure escape!",
        `Level ${state.next_level} unlocked: the next dungeon grows from ${state.grid_size}×${state.grid_size} to ${state.grid_size + 1}×${state.grid_size + 1}. Choose a mode to continue.${heartNote}`,
      ];
    if (kind === "won" && state.next_level === 7)
      return [
        "Treasure escape!",
        `Level 7 unlocked: the board stays at a readable 13×13, but randomized walls and dead ends now fortify the dungeon.${heartNote}`,
      ];
    if (kind === "won" && state.next_level < 10)
      return [
        "Treasure escape!",
        `Level ${state.next_level} unlocked: the board stays at 13×13 and the dungeon remains fortified with randomized walls and dead ends.${heartNote}`,
      ];
    if (kind === "won")
      return [
        "Treasure escape!",
        `Level ${state.next_level} unlocked: 13×13 remains the size, fortification increases, and the dragon now knows every wall — Hard instincts are active.${heartNote}`,
      ];
    if (kind === "escaped")
      if (state.life_spent)
        return [
          "A heart saved you.",
          `The dragon caught you, but one heart brought you safely home. ${state.hearts}/3 hearts remain for future escapes; you stay on Level ${state.level}.`,
        ];
      if (state.heart_banked)
        return [
          "Heart delivered!",
          `You brought the heart back to the portal. Your next run has ${state.hearts}/3 hearts. You remain on Level ${state.level}.`,
        ];

    if (kind === "escaped")
      return [
        "You escaped safely.",
        `You returned without treasure, so you remain on Level ${state.level}. Choose a mode to continue.`,
      ];
    return [
      "The dragon got you.",
      "The next run returns to Level 1: an 8×8 dungeon with all 3 hearts restored. Inspect this dungeon or choose a mode to try again.",
    ];
  }
  function showResult() {
    if (!lastResult) return;
    menuTitle.textContent = lastResult.title;
    menuCopy.textContent = lastResult.copy;
    dismissResult.hidden = false;
    menu.hidden = false;
    nextButton.textContent = "Results & next dungeon";
  }
  function showMainMenu() {
    lastResult = null;
    dismissResult.hidden = true;
    menuTitle.textContent = debugMode
      ? "Dungeon Escape debug"
      : "Dungeon Escape";
    menuCopy.textContent = debugMode
      ? "Choose a level, reveal the entire dungeon, and compare the opposite dragon as a ghost."
      : "Find the treasure, evade the sleeping dragon, and return to the portal.";
    menu.hidden = false;
    nextButton.textContent = "Main menu";
  }
  function connect() {
    if (socket?.readyState === WebSocket.OPEN) return;
    socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws${debugMode ? "?debug=1" : ""}`,
    );
    socket.onopen = () => debugLog("connected");
    socket.onmessage = (event) => {
      const next = JSON.parse(event.data);
      if (next.error) {
        debugLog("server error", next.error);
        menuCopy.textContent = next.error;
        menu.hidden = false;
        return;
      }
      const previous = state;
      state = next;
      debugLog("state", {
        level: state.level,
        moves: state.moves,
        player: state.player,
        dragon: state.dragon,
        treasure: state.treasure,
        status: state.status,
        dragon_awake: state.dragon_awake,
        hearts: state.hearts,
        heart: state.heart,
        has_heart: state.has_heart,
        hard_instincts: state.forced_hard,
        phantom: state.phantom,
        walls: {
          horizontal: state.horizontal_walls.length,
          vertical: state.vertical_walls.length,
          total: state.horizontal_walls.length + state.vertical_walls.length,
        },
      });
      if (!previous?.dragon_awake && state.dragon_awake)
        debugLog("dragon awakened");
      if (state.status !== "playing") debugLog("run ended", state.status);
      setUsernameEditable(false);
      playFeedback(previous, state);
      status.textContent = state.hint;
      status.hidden = state.status === "playing";
      if (state.status !== "playing" && !resultTimer) {
        const [title, copy] = resultCopy(state.status);
        lastResult = { title, copy };
        resultTimer = setTimeout(() => {
          showResult();
          resultTimer = null;
        }, 2000);
      }
      draw();
    };
    socket.onclose = () => {
      debugLog("disconnected");
      status.hidden = false;
      status.textContent = "Connection lost. Reload to reconnect.";
    };
  }
  function start(difficulty) {
    const username = usernameInput.value.trim().replace(/\s+/g, " ");
    if (!username) {
      menuCopy.textContent = "Enter an explorer name to start your ranked run.";
      usernameInput.focus();
      return;
    }
    wakeAudio();
    localStorage.setItem("dungeon-escape-username", username);
    clearTimeout(resultTimer);
    resultTimer = null;
    lastResult = null;
    state = null;
    dismissResult.hidden = true;
    nextButton.textContent = "Main menu";
    connect();
    const begin = () =>
      send({
        action: "start",
        difficulty,
        username,
        client_id: clientId,
        level: debugMode ? Number(debugLevelInput.value) : undefined,
      });
    if (socket.readyState === WebSocket.OPEN) begin();
    else socket.addEventListener("open", begin, { once: true });
    menu.hidden = true;
  }
  function move(direction) {
    if (state?.status === "playing") {
      debugLog("move", direction);
      wakeAudio();
      send({ action: "move", direction });
    }
  }
  function has(items, x, y) {
    return items.some((item) => item[0] === x && item[1] === y);
  }
  function sprite(name, x, y, size) {
    if (assets[name]) ctx.drawImage(assets[name], x, y, size, size);
  }
  function resize() {
    const box = canvas.getBoundingClientRect(),
      ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = box.width * ratio;
    canvas.height = box.height * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }
  function draw() {
    const width = canvas.clientWidth,
      height = canvas.clientHeight;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, width, height);
    if (!state) return;
    const pad = Math.min(width, height) * 0.025,
      hud = Math.max(68, height * 0.1),
      tile = Math.min(
        (width - pad * 2) / state.grid_size,
        (height - pad * 2 - hud) / state.grid_size,
      ),
      board = tile * state.grid_size,
      left = (width - board) / 2,
      top = pad + hud;
    const threat = state.forced_hard
      ? "Hard instincts"
      : state.hard_mode
        ? "Hard"
        : "Normal";
    ctx.fillStyle = "#f6f4e8";
    ctx.font = `700 ${Math.max(14, tile * 0.31)}px system-ui`;
    ctx.textAlign = "left";
    const hudY = top - Math.max(30, tile * 0.48);
    const hudPrefix = `Level ${state.level}   Moves ${state.moves}   ${state.grid_size}×${state.grid_size}   ${threat}   Hearts `;
    ctx.fillText(hudPrefix, left, hudY);
    const heartX = left + ctx.measureText(hudPrefix).width;
    const heartSize = Math.max(16, tile * 0.34);
    if (assets.heart)
      for (let index = 0; index < state.hearts; index++)
        ctx.drawImage(
          assets.heart,
          heartX + index * heartSize,
          hudY - heartSize * 0.82,
          heartSize,
          heartSize,
        );
    else {
      ctx.fillStyle = "#ff4055";
      ctx.fillText("♥".repeat(state.hearts), heartX, hudY);
    }
    ctx.fillStyle = "#f6f4e8";
    ctx.fillText(
      `${state.has_treasure ? "   Treasure ✓" : ""}${state.has_heart ? "   Heart ✓" : ""}`,
      heartX + heartSize * state.hearts,
      hudY,
    );
    if (state.hint === "The air feels warm nearby…") {
      ctx.fillStyle = "#ffd34d";
      ctx.font = `700 ${Math.max(13, tile * 0.24)}px system-ui`;
      ctx.fillText("⚠ The air feels warm nearby…", left, top - 10);
    }
    for (let y = 0; y < state.grid_size; y++)
      for (let x = 0; x < state.grid_size; x++)
        sprite(
          `tiles/floor_${((x + y) % 2) + 1}`,
          left + x * tile,
          top + y * tile,
          tile,
        );
    for (const [x, y] of state.scorched)
      sprite("scorch", left + x * tile, top + y * tile, tile);
    sprite(
      "portal",
      left + state.start[0] * tile,
      top + state.start[1] * tile,
      tile,
    );
    const treasureVisible =
      state.debug ||
      state.status !== "playing" ||
      has(state.visited, ...state.treasure) ||
      Math.max(
        Math.abs(state.treasure[0] - state.player[0]),
        Math.abs(state.treasure[1] - state.player[1]),
      ) <= 2;
    if (treasureVisible && !state.has_treasure)
      sprite(
        "treasure_open",
        left + state.treasure[0] * tile,
        top + state.treasure[1] * tile,
        tile,
      );
    const heartVisible =
      state.heart &&
      !state.has_heart &&
      (state.debug ||
        state.status !== "playing" ||
        has(state.visited, ...state.heart) ||
        Math.max(
          Math.abs(state.heart[0] - state.player[0]),
          Math.abs(state.heart[1] - state.player[1]),
        ) <= 2);
    if (heartVisible) {
      sprite(
        "heart",
        left + state.heart[0] * tile,
        top + state.heart[1] * tile,
        tile,
      );
    }
    if (state.debug || state.dragon_awake || state.status !== "playing")
      sprite(
        state.dragon_awake ? "dragon/awake" : "dragon/sleeping",
        left + state.dragon[0] * tile,
        top + state.dragon[1] * tile,
        tile,
      );
    for (let y = 0; y < state.grid_size; y++)
      for (let x = 0; x < state.grid_size; x++) {
        const seen =
          state.debug ||
          has(state.visited, x, y) ||
          Math.max(
            Math.abs(x - state.player[0]),
            Math.abs(y - state.player[1]),
          ) <= 2 ||
          state.status !== "playing";
        if (
          !seen &&
          !(
            state.dragon_awake &&
            x === state.dragon[0] &&
            y === state.dragon[1]
          )
        )
          sprite("fog", left + x * tile, top + y * tile, tile);
      }
    const thick = Math.max(5, tile * 0.18);
    for (const [x, y] of state.horizontal_walls)
      if (assets["tiles/wall_horizontal"])
        ctx.drawImage(
          assets["tiles/wall_horizontal"],
          left + x * tile,
          top + (y + 1) * tile - thick / 2,
          tile,
          thick,
        );
    for (const [x, y] of state.vertical_walls)
      if (assets["tiles/wall_vertical"])
        ctx.drawImage(
          assets["tiles/wall_vertical"],
          left + (x + 1) * tile - thick / 2,
          top + y * tile,
          thick,
          tile,
        );
    if (state.has_treasure) {
      const x = left + (state.treasure[0] + 0.5) * tile,
        y = top + (state.treasure[1] + 0.5) * tile,
        size = tile * 0.18;
      ctx.strokeStyle = "#ef5965";
      ctx.lineWidth = Math.max(3, tile * 0.07);
      ctx.beginPath();
      ctx.moveTo(x - size, y - size);
      ctx.lineTo(x + size, y + size);
      ctx.moveTo(x + size, y - size);
      ctx.lineTo(x - size, y + size);
      ctx.stroke();
    }
    sprite(
      state.moves % 2 ? "hero/walk" : "hero/idle",
      left + state.player[0] * tile,
      top + state.player[1] * tile,
      tile,
    );
    if (state.phantom) {
      const [x, y] = state.phantom.position,
        ghostX = left + (x + 0.5) * tile,
        ghostY = top + (y + 0.5) * tile,
        color = state.phantom.hard_mode
          ? "rgba(129,220,255,.75)"
          : "rgba(190,145,255,.75)";
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(ghostX, ghostY, tile * 0.28, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.font = `800 ${Math.max(10, tile * 0.22)}px system-ui`;
      ctx.textAlign = "center";
      ctx.fillText(
        state.phantom.hard_mode ? "H" : "N",
        ghostX,
        ghostY + tile * 0.08,
      );
    }
    if (performance.now() < wakeUntil) {
      const pulse = (Math.sin(performance.now() / 55) + 1) / 2,
        dragonX = left + (state.dragon[0] + 0.5) * tile,
        dragonY = top + (state.dragon[1] + 0.5) * tile;
      const glow = ctx.createRadialGradient(
        dragonX,
        dragonY,
        tile * 0.1,
        dragonX,
        dragonY,
        board * 0.7,
      );
      glow.addColorStop(0, `rgba(255,55,35,${0.5 + pulse * 0.22})`);
      glow.addColorStop(1, "rgba(70,0,5,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(left, top, board, board);
      ctx.fillStyle = `rgba(20,0,5,${0.22 + pulse * 0.14})`;
      ctx.fillRect(left, top, board, board);
      ctx.textAlign = "center";
      ctx.fillStyle = "#ffcf4f";
      ctx.font = `900 ${Math.max(22, tile * 0.56)}px system-ui`;
      ctx.fillText("THE DRAGON AWAKENS", left + board / 2, top + board * 0.46);
      ctx.fillStyle = "#fff1d4";
      ctx.font = `800 ${Math.max(14, tile * 0.27)}px system-ui`;
      ctx.fillText("RUN!", left + board / 2, top + board * 0.53);
    }
  }
  document
    .querySelectorAll("[data-mode]")
    .forEach((button) =>
      button.addEventListener("click", () => start(button.dataset.mode)),
    );
  document
    .querySelectorAll("[data-direction]")
    .forEach((button) =>
      button.addEventListener("click", () => move(button.dataset.direction)),
    );
  nextButton.addEventListener("click", () => {
    if (lastResult) showResult();
    else showMainMenu();
  });
  dismissResult.addEventListener("click", () => {
    menu.hidden = true;
  });
  soundButton.addEventListener("click", () => {
    muted = !muted;
    localStorage.setItem("dungeon-escape-muted", String(muted));
    updateSoundButton();
    if (!muted) wakeAudio();
  });
  async function showLeaderboard() {
    leaderboardBody.replaceChildren();
    const loading = document.createElement("tr");
    loading.innerHTML =
      '<td colspan="5" class="ranking-empty">Loading rankings…</td>';
    leaderboardBody.append(loading);
    leaderboard.hidden = false;
    try {
      const response = await fetch("/api/leaderboard");
      const { players } = await response.json();
      leaderboardBody.replaceChildren();
      if (!players.length) {
        const empty = document.createElement("tr");
        empty.innerHTML =
          '<td colspan="5" class="ranking-empty">No completed runs yet.</td>';
        leaderboardBody.append(empty);
        return;
      }
      players.forEach((player, index) => {
        const row = document.createElement("tr");
        [
          index + 1,
          player.username,
          player.wins,
          player.best_win_moves ?? "—",
          player.highest_win_streak,
        ].forEach((value) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.append(cell);
        });
        leaderboardBody.append(row);
      });
    } catch {
      leaderboardBody.replaceChildren();
      const error = document.createElement("tr");
      error.innerHTML =
        '<td colspan="5" class="ranking-empty">Rankings are unavailable right now.</td>';
      leaderboardBody.append(error);
    }
  }
  document
    .querySelector("#leaderboard-toggle")
    .addEventListener("click", showLeaderboard);
  document.querySelector("#leaderboard-close").addEventListener("click", () => {
    leaderboard.hidden = true;
  });
  rulesButton.addEventListener("click", () => {
    rules.hidden = false;
  });
  document.querySelector("#rules-close").addEventListener("click", () => {
    rules.hidden = true;
  });
  profileButton.addEventListener("click", () => {
    showMainMenu();
    setUsernameEditable(true);
    usernameInput.focus();
    usernameInput.select();
  });
  addEventListener("keydown", (event) => {
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      event.target.isContentEditable
    )
      return;
    const direction = keys[event.key];
    if (direction) {
      event.preventDefault();
      move(direction);
    }
  });
  canvas.addEventListener("pointerdown", (event) => {
    swipe = [event.clientX, event.clientY];
  });
  canvas.addEventListener("pointerup", (event) => {
    if (!swipe) return;
    const dx = event.clientX - swipe[0],
      dy = event.clientY - swipe[1];
    swipe = null;
    if (Math.max(Math.abs(dx), Math.abs(dy)) > 25)
      move(
        Math.abs(dx) > Math.abs(dy)
          ? dx > 0
            ? "right"
            : "left"
          : dy > 0
            ? "down"
            : "up",
      );
  });
  new ResizeObserver(resize).observe(canvas);
})();
