<script lang="ts">
  import { ChevronDown, ChevronRight, Columns3, LayoutGrid, TriangleAlert } from '@lucide/svelte';
  import AppTile from './AppTile.svelte';
  import TerminalCard from './TerminalCard.svelte';
  import { apps } from '../stores/apps.svelte';
  import { sessions } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';
  import type { AppView, Group, SessionView } from '../types';

  const groups = $derived.by(() => {
    const v = apps.view;
    if (!v) return [] as { group: Group; apps: AppView[] }[];
    const known = v.groups.length
      ? v.groups
      : [...new Set(v.apps.map((a) => a.group))].map((id) => ({ id, name: id, accent: 'slate', collapsed: false }));
    return known
      .map((g) => ({ group: g, apps: v.apps.filter((a) => a.group === g.id) }))
      .filter((g) => g.apps.length);
  });

  const accentOf = (appId: string) => {
    const a = apps.byId(appId);
    return apps.view?.groups.find((g) => g.id === a?.group)?.accent ?? 'slate';
  };

  const orphans = $derived(sessions.apps.filter((s) => !apps.byId(s.app)));
  const shown = $derived(sessions.apps);
  const maxSession = $derived(ui.maximized ? sessions.get(ui.maximized) : undefined);

  function isOpen(g: Group, list: AppView[]): boolean {
    if (list.some((a) => sessions.forApp(a.id).length)) return true;
    return ui.groupOpen[g.id] ?? !g.collapsed;
  }

  function sessionsOf(a: AppView): SessionView[] {
    return sessions.forApp(a.id);
  }

  // Esc leaves the maximized / tiled view
  function onKey(e: KeyboardEvent) {
    if (e.key !== 'Escape' || ui.confirm || ui.params || ui.paletteOpen || ui.packagePickerOpen) return;
    if (ui.searchOpen) return;
    if (ui.maximized) ui.maximize(null);
    else if (ui.tiled) ui.setTiled(false);
  }
</script>

<svelte:window onkeydown={onKey} />

{#if apps.view?.errors.length}
  <div class="cfg-error card" role="alert">
    <TriangleAlert size={18} />
    <div>
      <strong>apps.toml has {apps.view.errors.length === 1 ? 'an error' : `${apps.view.errors.length} errors`}</strong>
      {#if apps.view.apps.length}<span class="muted"> — the last good version stays in use until it is fixed.</span>{/if}
      <ul class="mono selectable">
        {#each apps.view.errors as err (err)}<li>{err}</li>{/each}
      </ul>
      <span class="muted mono">{apps.view.configPath}</span>
    </div>
  </div>
{/if}

{#if (ui.maximized && maxSession) || ui.tiled}
  <div class="focus-view">
    <div class="strip">
      <button class="btn sm ghost back" onclick={() => (ui.tiled ? ui.setTiled(false) : ui.maximize(null))} title="Back to the grid (Esc)">
        <LayoutGrid size={14} />Grid <kbd>Esc</kbd>
      </button>
      {#each groups as g (g.group.id)}
        {#each g.apps.filter((a) => !a.planned) as a (a.id)}
          {@const ss = sessionsOf(a)}
          {#if ss.length}
            {#each ss as s (s.name)}<AppTile app={a} accent={g.group.accent} session={s} compact />{/each}
          {:else}
            <AppTile app={a} accent={g.group.accent} compact />
          {/if}
        {/each}
      {/each}
    </div>
    {#if ui.tiled}
      <div class="tiled" style:--n={Math.min(shown.length, shown.length > 4 ? 3 : 2)}>
        {#each shown as s (s.name)}
          <TerminalCard session={s} app={apps.byId(s.app)} accent={accentOf(s.app)} mode="tile" />
        {:else}
          <p class="muted empty">Nothing is running.</p>
        {/each}
      </div>
    {:else if maxSession}
      <div class="maxed">
        <TerminalCard session={maxSession} app={apps.byId(maxSession.app)} accent={accentOf(maxSession.app)} mode="max" />
      </div>
    {/if}
  </div>
{:else}
  <div class="scroll">
    {#if apps.loading}
      <div class="grid">
        {#each [1, 2, 3, 4, 5, 6] as k (k)}<div class="skeleton tile-sk"></div>{/each}
      </div>
    {:else if !groups.length}
      <div class="empty-state">
        <h2>No apps to show</h2>
        <p class="muted">The hub reads its tiles from <span class="mono">{apps.view?.configPath ?? 'hub/apps.toml'}</span>.</p>
      </div>
    {/if}

    {#if sessions.live.length >= 3}
      <div class="toolbar">
        <span class="muted">{sessions.live.length} apps running</span>
        <button class="btn sm" onclick={() => ui.setTiled(true)}><Columns3 size={14} />Tile terminals</button>
      </div>
    {/if}

    {#each groups as g (g.group.id)}
      {@const open = isOpen(g.group, g.apps)}
      <section class="group" aria-labelledby={`g-${g.group.id}`}>
        <button
          class="group-head"
          id={`g-${g.group.id}`}
          aria-expanded={open}
          onclick={() => ui.toggleGroup(g.group.id, !open)}
        >
          {#if open}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
          <span class="swatch" style:background="var(--g-{g.group.accent})"></span>
          <span class="section-title">{g.group.name}</span>
          {#if !open}<span class="faint count">{g.apps.length}</span>{/if}
        </button>
        {#if open}
          <div class="grid">
            {#each g.apps as a (a.id)}
              {@const ss = sessionsOf(a)}
              {#each ss as s (s.name)}
                {#if ui.collapsed[s.name]}
                  <div class="cell tile-cell"><AppTile app={a} accent={g.group.accent} session={s} /></div>
                {:else}
                  <div class="cell run-cell"><TerminalCard session={s} app={a} accent={g.group.accent} /></div>
                {/if}
              {/each}
              {#if !ss.length || !a.singleton}
                <div class="cell tile-cell" class:wide={a.primary && !ss.length}>
                  <AppTile app={a} accent={g.group.accent} />
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      </section>
    {/each}

    {#if orphans.length}
      <section class="group">
        <div class="group-head static"><span class="section-title">Other sessions</span></div>
        <p class="muted note">These sessions run on the hub's tmux server but their app is no longer in apps.toml.</p>
        <div class="grid">
          {#each orphans as s (s.name)}
            <div class="cell run-cell"><TerminalCard session={s} /></div>
          {/each}
        </div>
      </section>
    {/if}
  </div>
{/if}

<style>
  .scroll {
    height: 100%;
    overflow: auto;
    padding: var(--s4) var(--s5) var(--s6);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    grid-auto-rows: 156px;
    grid-auto-flow: row dense;
    gap: var(--s4);
  }
  .cell {
    min-width: 0;
  }
  .tile-cell {
    grid-column: span 3;
  }
  .tile-cell.wide {
    grid-column: span 6;
  }
  .run-cell {
    grid-column: span 6;
    grid-row: span 2;
  }
  .tile-sk {
    grid-column: span 3;
    border-radius: var(--r-tile);
  }
  @media (max-width: 1400px) {
    .tile-cell {
      grid-column: span 4;
    }
    .tile-cell.wide {
      grid-column: span 8;
    }
    .run-cell {
      grid-column: span 12;
    }
  }
  .group {
    margin-bottom: var(--s5);
  }
  .group-head {
    display: flex;
    align-items: center;
    gap: var(--s2);
    margin: 0 0 var(--s3);
    padding: 4px 6px 4px 2px;
    border: 0;
    background: none;
    color: var(--muted);
    cursor: pointer;
    border-radius: 6px;
  }
  .group-head:hover {
    color: var(--text);
  }
  .group-head.static {
    cursor: default;
  }
  .swatch {
    width: 8px;
    height: 8px;
    border-radius: 2px;
  }
  .count {
    font-size: 12px;
  }
  .note {
    margin: -6px 0 var(--s3);
    font-size: 12.5px;
  }
  .toolbar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--s3);
    margin-bottom: var(--s3);
    font-size: 12.5px;
  }
  .cfg-error {
    display: flex;
    gap: var(--s3);
    margin: var(--s4) var(--s5) 0;
    padding: var(--s3) var(--s4);
    border-color: color-mix(in srgb, var(--error) 50%, var(--border));
    background: var(--error-soft);
    color: var(--error);
  }
  .cfg-error > div {
    color: var(--text);
    font-size: 13px;
  }
  .cfg-error ul {
    margin: 6px 0;
    padding-left: 18px;
    font-size: 12px;
  }
  .empty-state {
    padding: 80px 0;
    text-align: center;
  }
  .empty-state h2 {
    margin: 0 0 8px;
    font-size: 18px;
  }

  .focus-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: var(--s3) var(--s4) var(--s4);
    gap: var(--s3);
  }
  .strip {
    display: flex;
    align-items: center;
    gap: var(--s2);
    overflow-x: auto;
    padding-bottom: 2px;
    flex: none;
  }
  .back {
    flex: none;
  }
  .maxed {
    flex: 1;
    min-height: 0;
  }
  .tiled {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(var(--n), minmax(0, 1fr));
    grid-auto-rows: minmax(0, 1fr);
    gap: var(--s3);
  }
  .empty {
    margin: auto;
  }
</style>
