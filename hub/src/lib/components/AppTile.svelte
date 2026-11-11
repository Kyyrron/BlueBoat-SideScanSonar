<script lang="ts">
  import {
    AppWindow,
    FileText,
    FolderOpen,
    Info,
    Maximize2,
    Play,
    SlidersHorizontal,
    Square,
    TriangleAlert,
  } from '@lucide/svelte';
  import Menu, { type MenuItem } from './Menu.svelte';
  import { iconFor } from '../icons';
  import { api, errText } from '../ipc';
  import { ago, clock, exitText } from '../format';
  import { displayName, launchApp, run, stopSession } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';
  import type { AppView, SessionView } from '../types';

  let {
    app,
    accent = 'slate',
    session = null,
    compact = false,
  }: {
    app: AppView;
    accent?: string;
    /** a running session shown collapsed */
    session?: SessionView | null;
    /** slim strip item (maximized / tiled views) */
    compact?: boolean;
  } = $props();

  const Icon = $derived(iconFor(app.icon));
  const vt = $derived(session ? (app.singleton ? `vt-${app.id}` : `vt-s-${session.name}`) : `vt-${app.id}`);

  async function openLastLog() {
    try {
      const logs = await api.listLogs();
      const mine = logs.find((l) => l.app === app.id);
      if (!mine) {
        ui.toast('info', `${app.name} has no log yet`);
        return;
      }
      await api.openPath(mine.path);
    } catch (e) {
      ui.toast('error', 'Could not open the log', errText(e));
    }
  }

  const menu = $derived.by(() => {
    const items: MenuItem[] = [];
    for (const v of app.variants) {
      items.push({
        label: `Launch ${v.name}`,
        icon: Play,
        action: () => launchApp(app.id, { variant: v.id }),
        disabled: !app.available,
      });
    }
    if (app.params.length) {
      items.push({
        label: 'Launch with parameters…',
        icon: SlidersHorizontal,
        action: () => launchApp(app.id, { ask: true }),
        disabled: !app.available,
      });
    }
    if (items.length) items.push({ separator: true, label: '' });
    if (app.help) items.push({ label: 'What is this?', icon: Info, action: showHelp });
    items.push({ label: 'Open its folder', icon: FolderOpen, action: () => run('Could not open the folder', api.openAppFolder(app.id)) });
    items.push({ label: 'Open last log', icon: FileText, action: openLastLog });
    return items;
  });

  function showHelp() {
    void ui.ask({
      title: app.name,
      body: app.help ?? app.description,
      detail: `Runs: ${app.command}`,
      buttons: [{ label: 'OK', value: 'ok', kind: 'primary' }],
      cancel: 'ok',
    });
  }

  const lastRun = $derived.by(() => {
    const r = app.lastRun;
    if (!r) return 'Not run yet';
    if (r.endedMs == null) return `Started ${ago(r.startedMs, ui.now)}`;
    return `${ago(r.endedMs, ui.now)} · ${exitText(r.exitCode, r.signal)}`;
  });
  const lastBad = $derived((app.lastRun?.exitCode ?? 0) !== 0 || app.lastRun?.signal != null);
</script>

{#if compact}
  <button
    class="strip-item"
    class:on={!!session}
    title={session ? `Show ${displayName(session)}` : app.available ? `Launch ${app.name}` : (app.reason ?? '')}
    disabled={!session && (!app.available || app.planned)}
    onclick={() => (session ? ui.maximize(session.name) : launchApp(app.id))}
  >
    <span class="accent-bar" style:background="var(--g-{accent})"></span>
    <Icon size={15} />
    <span class="nm">{session ? displayName(session) : app.name}</span>
    {#if session}
      <span class="dot {session.state}" class:pulse={session.state === 'running'}></span>
    {:else if app.available && !app.planned}
      <Play size={13} />
    {/if}
  </button>
{:else if app.planned}
  <div class="tile planned" style:view-transition-name={vt}>
    <div class="row">
      <span class="icon ghost"><Icon size={20} /></span>
      <div class="titles">
        <div class="name">{app.name}</div>
        <div class="desc">{app.description}</div>
      </div>
    </div>
    <div class="foot">
      <span class="badge">Planned — not built</span>
    </div>
  </div>
{:else if session}
  <!-- a running app collapsed back to tile size -->
  <div class="tile running" style:view-transition-name={vt} style:--acc="var(--g-{accent})">
    <div class="row">
      <span class="icon"><Icon size={20} /></span>
      <div class="titles">
        <div class="name">
          <span class="dot {session.state}" class:pulse={session.state === 'running'}></span>
          {displayName(session)}
        </div>
        <div class="desc">
          {#if session.state === 'exited'}{exitText(session.exitCode, session.signal)}
          {:else if session.state === 'stopping'}Waiting for it to close…
          {:else}Running {clock(ui.now - session.startedMs)}{/if}
        </div>
      </div>
      <button class="icon-btn" title="Expand terminal" aria-label="Expand terminal" onclick={() => ui.setCollapsed(session.name, false)}>
        <Maximize2 size={15} />
      </button>
    </div>
    <div class="preview mono" title={session.lastLine}>{session.lastLine || ' '}</div>
    <div class="foot">
      <button class="btn sm ghost" disabled={!session.windows.length} onclick={() => run('Focus failed', api.focus(session.name))}>
        <AppWindow size={14} />Focus
      </button>
      {#if session.state !== 'exited'}
        <button class="btn sm ghost" disabled={session.state === 'stopping'} onclick={() => stopSession(session.name)}>
          <Square size={13} />Stop
        </button>
      {/if}
    </div>
  </div>
{:else}
  <div
    class="tile"
    class:primary={app.primary}
    class:unavailable={!app.available}
    style:view-transition-name={vt}
    style:--acc="var(--g-{accent})"
  >
    <div class="row">
      <span class="icon"><Icon size={app.primary ? 22 : 20} /></span>
      <div class="titles">
        <div class="name">
          {app.name}
          {#if app.optional}<span class="badge">optional</span>{/if}
          {#if app.warning}
            <span class="badge warn" title={app.warning}><TriangleAlert size={11} />{app.primary ? 'note' : ''}</span>
          {/if}
          {#if app.help}
            <button class="info" title="What is this?" aria-label={`About ${app.name}`} onclick={showHelp}><Info size={14} /></button>
          {/if}
        </div>
        <div class="desc" title={app.description}>{app.description}</div>
      </div>
    </div>
    {#if !app.available}
      <div class="reason" title={app.reason ?? ''}>{app.reason}</div>
    {:else if app.warning && app.primary}
      <div class="reason soft">{app.warning}</div>
    {/if}
    <div class="foot">
      <span class="last" class:bad={lastBad && app.lastRun?.endedMs != null} title={app.fallback ? `Runs: ${app.command}` : app.command}>
        {lastRun}
      </span>
      <Menu items={menu} label={`${app.name} actions`} />
      <button
        class="btn primary launch"
        disabled={!app.available}
        title={app.available ? (app.warning ?? `Launch ${app.name}`) : (app.reason ?? '')}
        onclick={() => launchApp(app.id)}
      >
        <Play size={14} />Launch
      </button>
    </div>
  </div>
{/if}

<style>
  .tile {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--s2);
    height: 100%;
    min-height: 148px;
    padding: var(--s4);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r-tile);
    transition:
      border-color var(--t-fast) var(--ease),
      background var(--t-fast) var(--ease);
  }
  .tile::before {
    content: '';
    position: absolute;
    left: 14px;
    right: 14px;
    top: -1px;
    height: 2px;
    border-radius: 0 0 2px 2px;
    background: var(--acc, var(--g-slate));
    opacity: 0.85;
  }
  .tile:hover {
    border-color: var(--border-strong);
  }
  .tile.primary .name {
    font-size: 16px;
  }
  .tile.unavailable .icon,
  .tile.unavailable .name,
  .tile.unavailable .desc {
    opacity: 0.55;
  }
  .tile.planned {
    background: transparent;
    border-style: dashed;
    border-color: var(--border-strong);
  }
  .tile.planned::before {
    display: none;
  }
  .row {
    display: flex;
    align-items: flex-start;
    gap: var(--s3);
  }
  .icon {
    display: grid;
    place-items: center;
    flex: none;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: color-mix(in srgb, var(--acc, var(--g-slate)) 14%, transparent);
    color: var(--acc, var(--g-slate));
  }
  .icon.ghost {
    background: var(--raised);
    color: var(--faint);
  }
  .titles {
    flex: 1;
    min-width: 0;
  }
  .name {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 14.5px;
    white-space: nowrap;
  }
  .desc {
    margin-top: 2px;
    color: var(--muted);
    font-size: 12.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .info {
    display: inline-grid;
    place-items: center;
    width: 20px;
    height: 20px;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: none;
    color: var(--muted);
    cursor: pointer;
  }
  .info:hover {
    color: var(--accent);
    background: var(--accent-soft);
  }
  .reason {
    font-size: 12.5px;
    color: var(--warning);
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .reason.soft {
    color: var(--muted);
  }
  .foot {
    display: flex;
    align-items: center;
    gap: var(--s2);
    margin-top: auto;
  }
  .last {
    flex: 1;
    min-width: 0;
    font-size: 12px;
    color: var(--faint);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .last.bad {
    color: color-mix(in srgb, var(--error) 80%, var(--muted));
  }
  .launch {
    padding: 0 14px;
  }
  .running .preview {
    padding: 6px 8px;
    border-radius: 6px;
    background: var(--term-bg);
    color: var(--muted);
    font-size: 11.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .running .foot {
    justify-content: flex-end;
  }
  .running .name .dot {
    margin-right: 2px;
  }

  .strip-item {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 34px;
    padding: 0 12px 0 14px;
    border-radius: 9px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--muted);
    font-size: 12.5px;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
  }
  .strip-item:hover:not(:disabled) {
    color: var(--text);
    border-color: var(--border-strong);
  }
  .strip-item.on {
    color: var(--text);
  }
  .strip-item:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .accent-bar {
    position: absolute;
    left: 0;
    top: 7px;
    bottom: 7px;
    width: 3px;
    border-radius: 0 3px 3px 0;
  }
  .nm {
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
