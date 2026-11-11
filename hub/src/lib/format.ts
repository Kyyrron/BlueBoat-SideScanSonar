// Small formatting helpers: ages, durations, sizes.

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v < 10 ? v.toFixed(1) : Math.round(v)} ${units[i]}`;
}

const pad = (n: number) => String(n).padStart(2, '0');

/** 12:04, 1:02:03 */
export function clock(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}

/** 2m14s, 48s, 1h05m */
export function duration(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m${pad(s % 60)}s`;
  return `${Math.floor(m / 60)}h${pad(m % 60)}m`;
}

function hhmm(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "just now", "3 min ago", "2 h ago", "yesterday 18:42", "4 Nov 18:42", "4 Nov 2025" */
export function ago(ms: number | null | undefined, now: number): string {
  if (!ms) return 'never';
  const d = now - ms;
  if (d < 45_000) return 'just now';
  if (d < 3_600_000) return `${Math.round(d / 60_000)} min ago`;
  const then = new Date(ms);
  const today = new Date(now);
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  if (ms >= startOfToday) return `${Math.round(d / 3_600_000)} h ago`;
  if (ms >= startOfToday - 86_400_000) return `yesterday ${hhmm(then)}`;
  const month = then.toLocaleString('en-GB', { month: 'short' });
  if (then.getFullYear() === today.getFullYear()) return `${then.getDate()} ${month} ${hhmm(then)}`;
  return `${then.getDate()} ${month} ${then.getFullYear()}`;
}

/** "exited 0", "exited 1", "killed (signal 9)", "ended" */
export function exitText(code: number | null, signal: number | null): string {
  if (signal != null) return `killed (signal ${signal})`;
  if (code != null) return `exited ${code}`;
  return 'ended';
}

/** Every whitespace-separated word of the query must match (any order);
 *  each word is a case-insensitive subsequence. Higher = better, -1 = no match. */
export function fuzzy(query: string, text: string): number {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return 0;
  let total = 0;
  for (const w of words) {
    const s = fuzzyWord(w, text);
    if (s < 0) return -1;
    total += s;
  }
  return total;
}

function fuzzyWord(q: string, text: string): number {
  const t = text.toLowerCase();
  const direct = t.indexOf(q);
  if (direct >= 0) return 1000 - direct;
  let ti = 0;
  let score = 0;
  let run = 0;
  for (const c of q) {
    const found = t.indexOf(c, ti);
    if (found < 0) return -1;
    run = found === ti ? run + 1 : 0;
    score += 10 + run * 5 - Math.min(found - ti, 9);
    ti = found + 1;
  }
  return score;
}

export function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
