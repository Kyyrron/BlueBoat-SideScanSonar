<script lang="ts">
  import {
    AppWindow,
    FolderOpen,
    Hammer,
    LayoutGrid,
    Maximize2,
    Play,
    ScrollText,
    Search,
    Settings,
    Square,
  } from '@lucide/svelte';
  import type { Component } from 'svelte';
  import { api } from '../ipc';
  import { fuzzy } from '../format';
  import { apps } from '../stores/apps.svelte';
  import { build } from '../stores/build.svelte';
  import { data } from '../stores/data.svelte';
  import { displayName, launchApp, run, sessions, stopSession } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';

  interface Cmd {
    id: string;
    label: string;
    hint?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: Component<any>;
    run: () => void;
  }

  let q = $state('');
  let sel = $state(0);
  let input: HTMLInputElement | undefined = $state();

  const commands = $derived.by(() => {
    const out: Cmd[] = [];
    for (const s of sessions.apps) {
      const n = displayName(s);
      out.push({ id: `show:${s.name}`, label: `Show terminal: ${n}`, hint: s.state, icon: Maximize2, run: () => {
        ui.view = 'apps';
        ui.maximize(s.name);
      } });
      if (s.windows.length) out.push({ id: `focus:${s.name}`, label: `Focus window: ${n}`, icon: AppWindow, run: () => run('Focus failed', api.focus(s.name)) });
      if (s.state !== 'exited') out.push({ id: `stop:${s.name}`, label: `Stop ${n}`, hint: 'closes its window', icon: Square, run: () => stopSession(s.name) });
    }
    for (const a of apps.list) {
      if (a.planned || !a.available) continue;
      out.push({ id: `launch:${a.id}`, label: `Launch ${a.name}`, hint: a.group, icon: Play, run: () => launchApp(a.id) });
      for (const v of a.variants) {
        out.push({ id: `launch:${a.id}:${v.id}`, label: `Launch ${v.name}`, hint: a.group, icon: Play, run: () => launchApp(a.id, { variant: v.id }) });
      }
    }
    out.push({ id: 'build:all', label: 'Build all packages', hint: 'Ctrl+B', icon: Hammer, run: () => build.start([]) });
    for (const p of build.packages) {
      out.push({ id: `build:${p}`, label: `Build ${p}`, hint: '--packages-select', icon: Hammer, run: () => build.start([p]) });
    }
    for (const c of data.cards ?? []) {
      for (const t of c.tabs) {
        if (!t.exists) continue;
        out.push({
          id: `data:${c.id}:${t.label}`,
          label: `Open ${c.name}${c.tabs.length > 1 ? ` · ${t.label}` : ''}`,
          hint: 'folder',
          icon: FolderOpen,
          run: () => run('Could not open the folder', api.openPath(t.path)),
        });
      }
    }
    out.push({ id: 'go:apps', label: 'Go to Apps', icon: LayoutGrid, run: () => (ui.view = 'apps') });
    out.push({ id: 'go:data', label: 'Go to Data', icon: FolderOpen, run: () => (ui.view = 'data') });
    out.push({ id: 'go:logs', label: 'Go to Logs', icon: ScrollText, run: () => (ui.view = 'logs') });
    out.push({ id: 'go:settings', label: 'Go to Settings', icon: Settings, run: () => (ui.view = 'settings') });
    return out;
  });

  const results = $derived.by(() => {
    if (!q.trim()) return commands.slice(0, 40);
    return commands
      .map((c) => ({ c, s: fuzzy(q, `${c.label} ${c.hint ?? ''}`) }))
      .filter((x) => x.s >= 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 40)
      .map((x) => x.c);
  });

  $effect(() => {
    if (ui.paletteOpen) {
      q = '';
      sel = 0;
      void build.loadPackages();
      queueMicrotask(() => input?.focus());
    }
  });

  $effect(() => {
    void q;
    sel = 0;
  });

  function close() {
    ui.paletteOpen = false;
  }

  function exec(c: Cmd | undefined) {
    if (!c) return;
    close();
    c.run();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      sel = Math.min(sel + 1, results.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      sel = Math.max(sel - 1, 0);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      exec(results[sel]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      close();
    }
  }
</script>

{#if ui.paletteOpen}
  <div class="backdrop" role="presentation" onpointerdown={(e) => e.target === e.currentTarget && close()}>
    <div class="palette card" role="dialog" aria-modal="true" aria-label="Command palette">
      <div class="search">
        <Search size={16} />
        <input
          bind:this={input}
          bind:value={q}
          onkeydown={onKey}
          placeholder="Launch, stop, focus, build, open…"
          aria-label="Search actions"
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-list"
        />
        <kbd>Esc</kbd>
      </div>
      <ul id="palette-list" role="listbox">
        {#each results as c, i (c.id)}
          <li>
            <button
              role="option"
              aria-selected={i === sel}
              class:sel={i === sel}
              onpointermove={() => (sel = i)}
              onclick={() => exec(c)}
            >
              <c.icon size={15} />
              <span class="lbl">{c.label}</span>
              {#if c.hint}<span class="hint">{c.hint}</span>{/if}
            </button>
          </li>
        {:else}
          <li class="none muted">No matching action.</li>
        {/each}
      </ul>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 110;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 12vh;
    background: var(--overlay);
  }
  .palette {
    width: min(640px, calc(100vw - 32px));
    overflow: hidden;
    box-shadow: var(--shadow);
    animation: rise var(--t-fast) var(--ease);
  }
  @keyframes rise {
    from {
      transform: translateY(-6px);
      opacity: 0;
    }
  }
  .search {
    display: flex;
    align-items: center;
    gap: var(--s3);
    padding: 0 var(--s4);
    height: 52px;
    border-bottom: 1px solid var(--border);
    color: var(--muted);
  }
  .search input {
    flex: 1;
    border: 0;
    outline: 0;
    background: transparent;
    font-size: 15px;
    color: var(--text);
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 6px;
    max-height: 52vh;
    overflow: auto;
  }
  li button {
    display: flex;
    align-items: center;
    gap: var(--s3);
    width: 100%;
    padding: 8px 10px;
    border: 0;
    border-radius: 7px;
    background: none;
    text-align: left;
    cursor: pointer;
    color: var(--text);
  }
  li button :global(svg) {
    color: var(--muted);
    flex: none;
  }
  li button.sel {
    background: var(--accent-soft);
  }
  li button.sel :global(svg) {
    color: var(--accent);
  }
  .lbl {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hint {
    color: var(--faint);
    font-size: 12px;
  }
  .none {
    padding: 14px 12px;
  }
</style>
