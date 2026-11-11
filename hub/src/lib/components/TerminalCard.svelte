<script lang="ts">
  import {
    AppWindow,
    ArrowDown,
    ArrowUp,
    ClipboardCopy,
    Eraser,
    FileText,
    FolderOpen,
    Maximize2,
    Minimize2,
    PanelTopClose,
    RotateCcw,
    Search,
    Square,
    Unplug,
    X,
  } from '@lucide/svelte';
  import Menu, { type MenuItem } from './Menu.svelte';
  import { iconFor } from '../icons';
  import { api } from '../ipc';
  import { clock, exitText } from '../format';
  import {
    allText,
    clearSearch,
    clearView,
    copyText,
    focusTerminal,
    searchTerm,
    terminal,
  } from '../terminal';
  import { displayName, forceStop, run, stopSession } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';
  import type { AppView, SessionView } from '../types';

  let {
    session,
    app,
    accent = 'slate',
    mode = 'card',
  }: {
    session: SessionView;
    app?: AppView;
    accent?: string;
    mode?: 'card' | 'max' | 'tile';
  } = $props();

  const Icon = $derived(iconFor(app?.icon));
  const vt = $derived(app && !app.singleton ? `vt-s-${session.name}` : `vt-${session.app}`);
  const exited = $derived(session.state === 'exited');
  const bad = $derived(exited && (session.signal != null || (session.exitCode ?? 0) !== 0));
  const stoppingFor = $derived(session.stopRequestedMs ? ui.now - session.stopRequestedMs : 0);
  const ctrlCSent = $derived(!!ui.ctrlCSent[session.name]);
  const searching = $derived(ui.searchOpen === session.name);

  let query = $state('');
  let searchInput: HTMLInputElement | undefined = $state();
  let notFound = $state(false);

  $effect(() => {
    if (searching) searchInput?.focus();
  });

  const stateText = $derived.by(() => {
    switch (session.state) {
      case 'starting':
        return 'Starting… waiting for its window';
      case 'running':
        return `Running ${clock(ui.now - session.startedMs)}`;
      case 'stopping':
        return session.restartPending ? 'Restarting — waiting for it to close…' : 'Waiting for the app to close…';
      case 'exited':
        return session.signal != null
          ? `Killed (signal ${session.signal})`
          : session.exitCode != null
            ? `Exited (code ${session.exitCode})`
            : 'Ended';
    }
    return '';
  });

  function find(back = false) {
    notFound = !!query && !searchTerm(session.name, query, back);
  }

  function closeSearch() {
    ui.searchOpen = null;
    clearSearch(session.name);
    focusTerminal(session.name);
  }

  async function copyAll() {
    const ok = await copyText(allText(session.name));
    ui.toast(ok ? 'success' : 'error', ok ? 'Terminal output copied' : 'Copy failed');
  }

  const menu = $derived.by(() => {
    const items: MenuItem[] = [
      { label: 'Copy all output', icon: ClipboardCopy, action: copyAll },
      { label: 'Search…', icon: Search, hint: 'Ctrl+Shift+F', action: () => (ui.searchOpen = session.name) },
      {
        label: 'Open log file',
        icon: FileText,
        disabled: !session.log,
        action: () => session.log && run('Could not open the log', api.openPath(session.log)),
      },
      { label: 'Clear view', icon: Eraser, hint: 'Clears this view only; the log keeps everything', action: () => clearView(session.name) },
    ];
    if (app) items.push({ label: 'Open its folder', icon: FolderOpen, action: () => run('Could not open the folder', api.openAppFolder(app.id)) });
    if (mode === 'card') {
      items.push({ separator: true, label: '' });
      items.push({
        label: 'Detach view',
        icon: Unplug,
        hint: 'Shrink to a tile; the app keeps running',
        action: () => ui.setCollapsed(session.name, true),
      });
    }
    if (!exited) {
      items.push({ separator: true, label: '' });
      items.push({
        label: ctrlCSent ? 'Kill session…' : 'Force stop…',
        icon: Square,
        danger: true,
        action: () => forceStop(session.name),
      });
    }
    return items;
  });

  function onHeaderDbl(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('button')) return;
    ui.maximize(ui.maximized === session.name ? null : session.name);
  }
</script>

<section
  class="tcard {mode}"
  class:exited
  class:bad
  style:view-transition-name={mode === 'card' ? vt : undefined}
  style:--acc="var(--g-{accent})"
  aria-label={`${displayName(session)} terminal`}
>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <header ondblclick={onHeaderDbl}>
    <span class="dot {bad ? 'exited-bad' : session.state}" class:pulse={session.state === 'running'}></span>
    <span class="ic"><Icon size={16} /></span>
    <span class="name">{displayName(session)}</span>
    {#if session.variant && app}
      <span class="badge">{app.variants.find((v) => v.id === session.variant)?.name ?? session.variant}</span>
    {/if}
    <span class="state" class:warn={session.state === 'stopping' || session.state === 'starting'} class:err={bad}>
      {stateText}
    </span>
    {#if !exited}<span class="pid mono">pid {session.pid}</span>{/if}
    {#if session.stale}
      <span class="badge warn" title="A package this app uses was rebuilt after it started — restart to use the new build">
        <span class="dot warn"></span>restart to use new build
      </span>
    {/if}
    <div class="grow"></div>
    <div class="tools">
      {#if !exited}
        <button
          class="icon-btn"
          title={session.windows.length ? 'Bring its window forward' : 'No window yet'}
          aria-label="Focus window"
          disabled={!session.windows.length}
          onclick={() => run('Focus failed', api.focus(session.name))}><AppWindow size={16} /></button
        >
      {/if}
      <button
        class="icon-btn"
        title={exited ? 'Launch again with the same parameters' : 'Restart: close politely, then launch again'}
        aria-label="Restart"
        disabled={session.state === 'stopping'}
        onclick={() => run('Restart failed', api.restart(session.name))}><RotateCcw size={16} /></button
      >
      {#if exited}
        <button class="icon-btn" title="Dismiss (the log file stays)" aria-label="Dismiss" onclick={() => run('Dismiss failed', api.dismiss(session.name))}>
          <X size={16} />
        </button>
      {:else}
        <button
          class="icon-btn danger"
          title={app?.window === false || app?.stop === 'ctrl-c' ? 'Stop (Ctrl-C, the polite stop of a launch file)' : 'Stop: close its window, like its ✕'}
          aria-label="Stop"
          disabled={session.state === 'stopping'}
          onclick={() => stopSession(session.name)}><Square size={15} /></button
        >
      {/if}
      {#if mode === 'card'}
        <button class="icon-btn" title="Collapse to a tile" aria-label="Collapse" onclick={() => ui.setCollapsed(session.name, true)}>
          <PanelTopClose size={16} />
        </button>
      {/if}
      <button
        class="icon-btn"
        title={mode === 'max' ? 'Restore (Esc)' : 'Maximize'}
        aria-label={mode === 'max' ? 'Restore' : 'Maximize'}
        onclick={() => ui.maximize(mode === 'max' ? null : session.name)}
      >
        {#if mode === 'max'}<Minimize2 size={16} />{:else}<Maximize2 size={16} />{/if}
      </button>
      <Menu items={menu} label="Terminal actions" />
    </div>
  </header>

  {#if session.state === 'stopping'}
    <div class="banner warn" role="status">
      <span>
        Waiting for {displayName(session)} to close — it may be asking something in its own window.
        {#if stoppingFor >= 10_000}<span class="muted"> ({Math.round(stoppingFor / 1000)} s)</span>{/if}
      </span>
      <div class="grow"></div>
      {#if session.windows.length}
        <button class="btn sm" onclick={() => run('Focus failed', api.focus(session.name))}>Show window</button>
      {/if}
      <button class="btn sm ghost" onclick={() => run('Could not cancel', api.cancelStop(session.name))}>Keep running</button>
      {#if stoppingFor >= 10_000 || ctrlCSent}
        <button class="btn sm danger-ghost" onclick={() => forceStop(session.name)}>
          {ctrlCSent ? 'Kill session…' : 'Force stop…'}
        </button>
      {/if}
    </div>
  {:else if exited}
    <div class="banner" class:err={bad} role="status">
      <span>
        {bad ? `${displayName(session)} ${exitText(session.exitCode, session.signal)}` : `${displayName(session)} closed`}
        — output kept below.
      </span>
      <div class="grow"></div>
      {#if session.log}
        <button class="btn sm ghost" onclick={() => session.log && run('Could not open the log', api.openPath(session.log))}>
          <FileText size={14} />Log
        </button>
      {/if}
      <button class="btn sm" onclick={() => run('Dismiss failed', api.dismiss(session.name))}>Dismiss</button>
      <button class="btn sm primary" onclick={() => run('Restart failed', api.restart(session.name))}>
        <RotateCcw size={13} />Restart
      </button>
    </div>
  {/if}

  <div class="body" role="presentation" onpointerdown={() => (ui.activeTerm = session.name)}>
    <div class="host" use:terminal={session.name}></div>
    {#if searching}
      <div class="search card">
        <Search size={14} />
        <input
          bind:this={searchInput}
          bind:value={query}
          placeholder="Find in output"
          class:nf={notFound}
          onkeydown={(e) => {
            if (e.key === 'Enter') find(e.shiftKey);
            if (e.key === 'Escape') {
              e.stopPropagation();
              closeSearch();
            }
          }}
          oninput={() => find()}
        />
        <button class="icon-btn" aria-label="Previous match" onclick={() => find(true)}><ArrowUp size={14} /></button>
        <button class="icon-btn" aria-label="Next match" onclick={() => find()}><ArrowDown size={14} /></button>
        <button class="icon-btn" aria-label="Close search" onclick={closeSearch}><X size={14} /></button>
      </div>
    {/if}
  </div>
</section>

<style>
  .tcard {
    position: relative;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r-tile);
    overflow: hidden;
  }
  .tcard::before {
    content: '';
    position: absolute;
    left: 14px;
    right: 14px;
    top: 0;
    height: 2px;
    border-radius: 0 0 2px 2px;
    background: var(--acc);
    opacity: 0.85;
    z-index: 2;
  }
  .tcard.max {
    box-shadow: var(--shadow);
  }
  .tcard.bad {
    border-color: color-mix(in srgb, var(--error) 45%, var(--border));
  }
  .tcard.bad::before {
    background: var(--error);
  }
  header {
    display: flex;
    align-items: center;
    gap: var(--s2);
    min-height: 46px;
    padding: 6px 8px 6px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
    cursor: default;
  }
  .exited header {
    background: color-mix(in srgb, var(--raised) 70%, var(--surface));
  }
  .bad header {
    background: color-mix(in srgb, var(--error) 7%, var(--surface));
  }
  .ic {
    display: inline-grid;
    color: var(--acc);
  }
  .name {
    font-weight: 600;
    white-space: nowrap;
  }
  .state {
    color: var(--muted);
    font-size: 12.5px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .state.warn {
    color: var(--warning);
  }
  .state.err {
    color: var(--error);
  }
  .pid {
    color: var(--faint);
    font-size: 11.5px;
  }
  .grow {
    flex: 1;
  }
  .tools {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .banner {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 7px 10px 7px 14px;
    font-size: 12.5px;
    border-bottom: 1px solid var(--border);
    background: var(--raised);
  }
  .banner.warn {
    background: var(--warning-soft);
    color: color-mix(in srgb, var(--warning) 70%, var(--text));
  }
  .banner.err {
    background: var(--error-soft);
  }
  .body {
    position: relative;
    flex: 1;
    min-height: 0;
    background: var(--term-bg);
  }
  .host {
    position: absolute;
    inset: 0;
  }
  .search {
    position: absolute;
    top: 8px;
    right: 14px;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 4px 4px 10px;
    border-radius: 10px;
    box-shadow: var(--shadow);
    color: var(--muted);
  }
  .search input {
    width: 220px;
    height: 28px;
    border: 0;
    outline: 0;
    background: transparent;
    padding: 0 6px;
  }
  .search input.nf {
    color: var(--error);
  }
</style>
