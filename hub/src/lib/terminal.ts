// One xterm.js instance per tmux session, kept alive while the session
// exists and moved between containers (card, maximized view, tiled view)
// instead of being recreated. Bytes come from the Rust control-mode client.

import { Terminal, type ITheme } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { WebglAddon } from '@xterm/addon-webgl';
import { api, Channel } from './ipc';
import { b64ToBytes } from './format';
import type { TermMsg } from './types';

interface Handle {
  session: string;
  term: Terminal;
  fit: FitAddon;
  search: SearchAddon;
  host: HTMLDivElement;
  opened: boolean;
  channel: Channel<TermMsg> | null;
  ro: ResizeObserver | null;
  size: string;
  disposed: boolean;
  retry: number | null;
}

const handles = new Map<string, Handle>();
let fontSize = 13;

/** Keys the hub handles itself; xterm must not swallow them. */
export function isHubShortcut(e: KeyboardEvent): boolean {
  if (!e.ctrlKey || e.altKey || e.metaKey) return false;
  const k = e.key.toLowerCase();
  if (!e.shiftKey && (k === 'k' || k === 'b' || /^[1-9]$/.test(k))) return true;
  if (e.shiftKey && (k === 'f' || k === 'c' || k === 'v')) return true;
  return false;
}

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function currentTheme(): ITheme {
  const light = document.documentElement.getAttribute('data-theme') === 'light' ||
    (!document.documentElement.hasAttribute('data-theme') && matchMedia('(prefers-color-scheme: light)').matches);
  const base: ITheme = {
    background: cssVar('--term-bg', '#0d131a'),
    foreground: cssVar('--term-fg', '#d7dee6'),
    cursor: cssVar('--term-cursor', '#2dd4bf'),
    cursorAccent: cssVar('--term-bg', '#0d131a'),
    selectionBackground: cssVar('--term-selection', 'rgba(45,212,191,.28)'),
  };
  return light
    ? {
        ...base,
        black: '#1d2733', red: '#c62828', green: '#2e7d32', yellow: '#a16207', blue: '#1d4ed8',
        magenta: '#7e22ce', cyan: '#0e7490', white: '#64748b', brightBlack: '#475569',
        brightRed: '#dc2626', brightGreen: '#15803d', brightYellow: '#b45309', brightBlue: '#2563eb',
        brightMagenta: '#9333ea', brightCyan: '#0891b2', brightWhite: '#1e293b',
      }
    : {
        ...base,
        black: '#1a2430', red: '#f87171', green: '#4ade80', yellow: '#fbbf24', blue: '#60a5fa',
        magenta: '#c084fc', cyan: '#2dd4bf', white: '#d7dee6', brightBlack: '#5d6b7b',
        brightRed: '#fca5a5', brightGreen: '#86efac', brightYellow: '#fcd34d', brightBlue: '#93c5fd',
        brightMagenta: '#d8b4fe', brightCyan: '#5eead4', brightWhite: '#f8fafc',
      };
}

function create(session: string): Handle {
  const term = new Terminal({
    scrollback: 10_000,
    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
    fontSize,
    lineHeight: 1.2,
    cursorBlink: false,
    cursorStyle: 'bar',
    convertEol: false,
    allowProposedApi: true,
    theme: currentTheme(),
  });
  const fit = new FitAddon();
  const search = new SearchAddon();
  term.loadAddon(fit);
  term.loadAddon(search);
  term.loadAddon(
    new WebLinksAddon((_e, uri) => {
      void api.openUrl(uri).catch(() => {});
    }),
  );
  term.attachCustomKeyEventHandler((e) => {
    if (isHubShortcut(e)) {
      if (e.type === 'keydown' && e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'c') {
        const sel = term.getSelection();
        if (sel) void copyText(sel);
      }
      if (e.type === 'keydown' && e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'v') {
        void navigator.clipboard
          ?.readText()
          .then((t) => t && term.paste(t))
          .catch(() => {});
      }
      return false;
    }
    return true;
  });
  term.onData((d) => void api.writeStdin(session, d).catch(() => {}));
  const host = document.createElement('div');
  host.className = 'xterm-host';
  const h: Handle = {
    session,
    term,
    fit,
    search,
    host,
    opened: false,
    channel: null,
    ro: null,
    size: '',
    disposed: false,
    retry: null,
  };
  handles.set(session, h);
  return h;
}

function connect(h: Handle) {
  if (h.disposed) return;
  const ch = new Channel<TermMsg>();
  ch.onmessage = (m) => {
    if (h.disposed || h.channel !== ch) return;
    if (m.kind === 'history') {
      h.term.reset();
      h.term.write(b64ToBytes(m.data));
    } else if (m.kind === 'output') {
      h.term.write(b64ToBytes(m.data));
    } else {
      // client went away (tmux restarted it): reattach shortly
      scheduleReconnect(h);
    }
  };
  h.channel = ch;
  api
    .attach(h.session, ch)
    .then(() => {
      h.size = '';
      resizeToFit(h);
    })
    .catch(() => scheduleReconnect(h));
}

function scheduleReconnect(h: Handle) {
  if (h.disposed || h.retry != null) return;
  h.retry = window.setTimeout(() => {
    h.retry = null;
    connect(h);
  }, 1000);
}

function resizeToFit(h: Handle) {
  if (!h.opened || !h.host.isConnected) return;
  const r = h.host.getBoundingClientRect();
  if (r.width < 40 || r.height < 30) return;
  try {
    h.fit.fit();
  } catch {
    return;
  }
  const size = `${h.term.cols}x${h.term.rows}`;
  if (size !== h.size) {
    h.size = size;
    void api.resize(h.session, h.term.cols, h.term.rows).catch(() => {});
  }
}

/** Svelte action: show the session's terminal inside `node`. */
export function terminal(node: HTMLElement, session: string) {
  let h = handles.get(session) ?? create(session);
  const attach = () => {
    node.appendChild(h.host);
    if (!h.opened) {
      h.term.open(h.host);
      try {
        const gl = new WebglAddon();
        gl.onContextLoss(() => gl.dispose());
        h.term.loadAddon(gl);
      } catch {
        /* no WebGL: xterm's DOM renderer takes over */
      }
      h.opened = true;
      connect(h);
    }
    h.ro?.disconnect();
    h.ro = new ResizeObserver(() => resizeToFit(h));
    h.ro.observe(node);
    requestAnimationFrame(() => resizeToFit(h));
  };
  attach();
  return {
    update(next: string) {
      if (next === session) return;
      session = next;
      h = handles.get(session) ?? create(session);
      attach();
    },
    destroy() {
      if (h.host.parentNode === node) {
        h.ro?.disconnect();
        h.ro = null;
        node.removeChild(h.host);
      }
    },
  };
}

export function disposeTerminal(session: string) {
  const h = handles.get(session);
  if (!h) return;
  h.disposed = true;
  if (h.retry != null) clearTimeout(h.retry);
  h.ro?.disconnect();
  h.host.remove();
  h.term.dispose();
  handles.delete(session);
}

export function focusTerminal(session: string) {
  handles.get(session)?.term.focus();
}

export function termOf(session: string): Terminal | undefined {
  return handles.get(session)?.term;
}

export function searchTerm(session: string, q: string, backwards = false): boolean {
  const h = handles.get(session);
  if (!h || !q) return false;
  const opts = {
    caseSensitive: false,
    decorations: {
      matchBackground: '#f59e0b55',
      activeMatchBackground: '#2dd4bf88',
      matchOverviewRuler: '#f59e0b',
      activeMatchColorOverviewRuler: '#2dd4bf',
    },
  };
  return backwards ? h.search.findPrevious(q, opts) : h.search.findNext(q, opts);
}

export function clearSearch(session: string) {
  handles.get(session)?.search.clearDecorations();
}

export function allText(session: string): string {
  const t = handles.get(session)?.term;
  if (!t) return '';
  const buf = t.buffer.active;
  const lines: string[] = [];
  for (let i = 0; i < buf.length; i++) lines.push(buf.getLine(i)?.translateToString(true) ?? '');
  while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
  return lines.join('\n');
}

export function clearView(session: string) {
  handles.get(session)?.term.clear();
}

export function retheme() {
  const theme = currentTheme();
  for (const h of handles.values()) h.term.options.theme = theme;
}

export function setTerminalFontSize(px: number) {
  fontSize = px;
  for (const h of handles.values()) {
    h.term.options.fontSize = px;
    h.size = '';
    resizeToFit(h);
  }
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    return ok;
  }
}
