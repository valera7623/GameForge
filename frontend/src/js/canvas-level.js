/**
 * Canvas renderer for level tilemaps.
 */

const COLORS = {
  0: "#0b0d12",
  1: "#2a3142",
  2: "#3a4a3a",
  3: "#f0a35e",
  4: "#e85d5d",
  5: "#2a6f9e",
  6: "#e6c35c",
};

export function renderLevel(canvas, level, cellSize = 14) {
  if (!canvas || !level?.tiles) return;
  const tiles = level.tiles;
  const h = tiles.length;
  const w = tiles[0]?.length || 0;
  canvas.width = w * cellSize;
  canvas.height = h * cellSize;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const t = tiles[y][x];
      ctx.fillStyle = COLORS[t] ?? "#555";
      ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
    }
  }

  // Entities
  ctx.fillStyle = "#ff6b6b";
  for (const e of level.enemies || []) {
    ctx.beginPath();
    ctx.arc(e.x * cellSize + cellSize / 2, e.y * cellSize + cellSize / 2, cellSize * 0.35, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = "#5dce7b";
  if (level.spawn) {
    ctx.fillRect(level.spawn.x * cellSize + 2, level.spawn.y * cellSize + 2, cellSize - 4, cellSize - 4);
  }

  ctx.fillStyle = "#3dd6c6";
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
