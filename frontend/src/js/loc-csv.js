/**
 * Client-side CSV → localization texts parser.
 * Accepts key + source column (source|en|text|value|string|english).
 */

const SOURCE_HEADERS = new Set(["source", "en", "text", "value", "string", "english", "src"]);
const KEY_HEADERS = new Set(["key", "id", "name", "string_id", "stringid"]);

/**
 * Split one CSV line respecting quotes. Delimiter is "," or ";".
 * @param {string} line
 * @param {string} delim
 * @returns {string[]}
 */
export function splitCsvLine(line, delim = ",") {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === delim) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

/**
 * @param {string} headerLine
 * @returns {string}
 */
export function detectDelimiter(headerLine) {
  const commas = (headerLine.match(/,/g) || []).length;
  const semis = (headerLine.match(/;/g) || []).length;
  return semis > commas ? ";" : ",";
}

/**
 * @param {string} content raw CSV text (UTF-8, optional BOM)
 * @returns {{ texts: Record<string, string>, warnings: string[], keyCount: number }}
 */
export function parseSourceCsv(content) {
  if (content == null || String(content).trim() === "") {
    throw new Error("empty_csv");
  }

  let raw = String(content).replace(/^\uFEFF/, "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = raw.split("\n").filter((l) => l.trim() !== "");
  if (lines.length < 2) {
    throw new Error("csv_need_header_and_row");
  }

  const delim = detectDelimiter(lines[0]);
  const headers = splitCsvLine(lines[0], delim).map((h) => h.trim().toLowerCase());
  let keyIdx = headers.findIndex((h) => KEY_HEADERS.has(h));
  let sourceIdx = headers.findIndex((h) => SOURCE_HEADERS.has(h));

  // Fallback: col0 = key, col1 = source when headers are unknown but ≥2 columns
  if (keyIdx < 0 && sourceIdx < 0 && headers.length >= 2) {
    keyIdx = 0;
    sourceIdx = 1;
  } else {
    if (keyIdx < 0) throw new Error("csv_no_key_column");
    if (sourceIdx < 0) {
      // Prefer first non-key column
      sourceIdx = headers.findIndex((_, i) => i !== keyIdx);
    }
    if (sourceIdx < 0) throw new Error("csv_no_source_column");
  }

  const texts = {};
  const warnings = [];
  const seen = new Map();

  for (let r = 1; r < lines.length; r++) {
    const cols = splitCsvLine(lines[r], delim);
    const key = (cols[keyIdx] ?? "").trim();
    const value = (cols[sourceIdx] ?? "").trim();
    if (!key) {
      warnings.push(`row_${r + 1}_empty_key`);
      continue;
    }
    if (seen.has(key)) {
      throw new Error(`csv_duplicate_key:${key}`);
    }
    seen.set(key, r + 1);
    texts[key] = value;
  }

  const keyCount = Object.keys(texts).length;
  if (keyCount === 0) {
    throw new Error("csv_no_rows");
  }

  return { texts, warnings, keyCount };
}

/**
 * Map parser error codes to i18n keys (caller applies t()).
 * @param {Error|string} err
 * @returns {{ key: string, params?: Record<string, string> }}
 */
export function csvErrorToI18n(err) {
  const msg = typeof err === "string" ? err : err?.message || "csv_parse_failed";
  if (msg.startsWith("csv_duplicate_key:")) {
    return { key: "loc.csv_duplicate", params: { key: msg.slice("csv_duplicate_key:".length) } };
  }
  const map = {
    empty_csv: "loc.csv_empty",
    csv_need_header_and_row: "loc.csv_need_rows",
    csv_no_key_column: "loc.csv_no_key",
    csv_no_source_column: "loc.csv_no_source",
    csv_no_rows: "loc.csv_no_rows",
  };
  return { key: map[msg] || "loc.csv_parse_failed" };
}
