/**
 * Canvas renderer + interactive editor for level tilemaps.
 */

export const TILE = {
  empty: 0,
  wall: 1,
  floor: 2,
  door: 3,
  trap: 4,
  water: 5,
  chest: 6,
};

const DEFAULT_COLORS = {
  0: "#0b0d12",
  1: "#2a3142",
  2: "#3a4a3a",
  3: "#f0a35e",
  4: "#e85d5d",
  5: "#2a6f9e",
  6: "#e6c35c",
};

const STYLE_COLORS = {
  dungeon: DEFAULT_COLORS,
  cave: { 0: "#0a0c10", 1: "#3a322c", 2: "#4a4038", 3: "#c4a574", 4: "#c45c3a", 5: "#1f4f5a", 6: "#d4b45c" },
  temple: { 0: "#0c1014", 1: "#4a4038", 2: "#5a5048", 3: "#e0c080", 4: "#b04040", 5: "#2a6088", 6: "#f0d060" },
  city: { 0: "#101218", 1: "#3a3e4a", 2: "#4a5060", 3: "#88a0c0", 4: "#d06050", 5: "#306090", 6: "#e0c050" },
  winter: { 0: "#0e1420", 1: "#3a4a5a", 2: "#d8e8f0", 3: "#80b0d0", 4: "#c05070", 5: "#a0d0f0", 6: "#f0e090" },
  sci_fi: { 0: "#060810", 1: "#1a2030", 2: "#142838", 3: "#40e0d0", 4: "#ff4060", 5: "#2060a0", 6: "#c0ff60" },
  desert: { 0: "#1a140c", 1: "#6a5030", 2: "#c8a878", 3: "#a08050", 4: "#c06030", 5: "#5080a0", 6: "#e0c040" },
};

export function colorsForStyle(style) {
  const key = String(style || "dungeon").replace(/-/g, "_");
  return STYLE_COLORS[key] || DEFAULT_COLORS;
}

export function renderLevel(canvas, level, cellSize = 14) {
  if (!canvas || !level?.tiles) return;
  const tiles = level.tiles;
  const h = tiles.length;
  const w = tiles[0]?.length || 0;
  const colors = colorsForStyle(level.style);
  canvas.width = w * cellSize;
  canvas.height = h * cellSize;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const t = tiles[y][x];
      ctx.fillStyle = colors[t] ?? "#555";
      ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
    }
  }

  ctx.fillStyle = "#ff6b6b";
  for (const e of level.enemies || []) {
    ctx.beginPath();
    ctx.arc(e.x * cellSize + cellSize / 2, e.y * cellSize + cellSize / 2, cellSize * 0.35, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = "#f5d76e";
  for (const it of level.items || []) {
    if (tiles[it.y]?.[it.x] === TILE.chest) continue;
    ctx.fillRect(it.x * cellSize + 3, it.y * cellSize + 3, cellSize - 6, cellSize - 6);
  }

  ctx.fillStyle = "#5dce7b";
  if (level.spawn) {
    ctx.fillRect(level.spawn.x * cellSize + 2, level.spawn.y * cellSize + 2, cellSize - 4, cellSize - 4);
  }

  if (level.exit) {
    ctx.strokeStyle = "#3dd6c6";
    ctx.lineWidth = 2;
    ctx.strokeRect(level.exit.x * cellSize + 2, level.exit.y * cellSize + 2, cellSize - 4, cellSize - 4);
  }
}

export function downloadCanvasPNG(canvas, filename = "level.png") {
  const a = document.createElement("a");
  a.href = canvas.toDataURL("image/png");
  a.download = filename;
  a.click();
}

/**
 * Interactive editor: paint tiles / place entities.
 * @returns {{ setTool: Function, getLevel: Function, setLevel: Function, destroy: Function, redraw: Function }}
 */
export function mountLevelEditor(canvas, initialLevel, opts = {}) {
  const cellSize = opts.cellSize ?? 14;
  let level = structuredClone(initialLevel);
  let tool = opts.tool || "wall";
  let painting = false;

  function redraw() {
    renderLevel(canvas, level, cellSize);
  }

  function cellFromEvent(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = Math.floor(((e.clientX - rect.left) * scaleX) / cellSize);
    const y = Math.floor(((e.clientY - rect.top) * scaleY) / cellSize);
    if (!level?.tiles?.[y] || x < 0 || x >= level.width) return null;
    return { x, y };
  }

  function applyAt(x, y) {
    if (!level?.tiles?.[y]) return;
    level.enemies = level.enemies || [];
    level.items = level.items || [];

    if (tool === "wall") {
      level.tiles[y][x] = TILE.wall;
    } else if (tool === "floor") {
      level.tiles[y][x] = TILE.floor;
    } else if (tool === "empty") {
      level.tiles[y][x] = TILE.empty;
    } else if (tool === "trap") {
      level.tiles[y][x] = TILE.trap;
    } else if (tool === "water") {
      level.tiles[y][x] = TILE.water;
    } else if (tool === "door") {
      level.tiles[y][x] = TILE.door;
    } else if (tool === "chest" || tool === "treasure") {
      level.tiles[y][x] = TILE.chest;
      level.items = level.items.filter((it) => !(it.x === x && it.y === y));
      level.items.push({ type: "gold", x, y });
    } else if (tool === "enemy") {
      level.enemies = level.enemies.filter((en) => !(en.x === x && en.y === y));
      level.enemies.push({ type: "skeleton", x, y, hp: 40 });
      if (level.tiles[y][x] === TILE.wall || level.tiles[y][x] === TILE.empty) {
        level.tiles[y][x] = TILE.floor;
      }
    } else if (tool === "erase_enemy") {
      level.enemies = level.enemies.filter((en) => !(en.x === x && en.y === y));
    } else if (tool === "erase_treasure") {
      level.items = level.items.filter((it) => !(it.x === x && it.y === y));
      if (level.tiles[y][x] === TILE.chest) level.tiles[y][x] = TILE.floor;
    }

    level.width = level.tiles[0]?.length || level.width;
    level.height = level.tiles.length;
    redraw();
    opts.onChange?.(level);
  }

  function onDown(e) {
    painting = true;
    const c = cellFromEvent(e);
    if (c) applyAt(c.x, c.y);
  }
  function onMove(e) {
    if (!painting) return;
    if (tool === "enemy" || tool === "erase_enemy" || tool === "erase_treasure" || tool === "treasure" || tool === "chest") {
      return;
    }
    const c = cellFromEvent(e);
    if (c) applyAt(c.x, c.y);
  }
  function onUp() {
    painting = false;
  }

  canvas.style.cursor = "crosshair";
  canvas.addEventListener("mousedown", onDown);
  canvas.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);

  redraw();

  return {
    setTool(t) {
      tool = t;
    },
    getLevel() {
      return structuredClone(level);
    },
    setLevel(next) {
      level = structuredClone(next);
      redraw();
    },
    redraw,
    destroy() {
      canvas.removeEventListener("mousedown", onDown);
      canvas.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    },
  };
}
