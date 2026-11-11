<script lang="ts">
  import { ChevronDown, ChevronRight, ExternalLink, File, Folder, FolderOpen, Play, RefreshCw } from '@lucide/svelte';
  import { iconFor } from '../icons';
  import { api, errText } from '../ipc';
  import { ago, bytes } from '../format';
  import { data } from '../stores/data.svelte';
  import { doLaunch, run } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';
  import type { DataCard, DataEntry } from '../types';

  let tab = $state<Record<string, number>>({});
  let expanded = $state<Record<string, boolean>>({});

  async function act(e: DataEntry) {
    if (e.action) {
      const ok = await doLaunch(e.action.app, { [e.action.param]: e.action.target }, null);
      if (ok) ui.toast('success', `${e.action.label}: ${e.name}`);
    } else {
      await open(e.path);
    }
  }

  async function open(path: string) {
    try {
      await api.openPath(path);
    } catch (err) {
      ui.toast('error', 'Could not open it', errText(err));
    }
  }

  const cur = (c: DataCard) => c.tabs[Math.min(tab[c.id] ?? 0, c.tabs.length - 1)];
</script>

<div class="scroll">
  <div class="head">
    <div>
      <h2>Data</h2>
      <p class="muted">Read-only: the hub lists, sizes and opens these folders. It never moves, renames or deletes anything in them.</p>
    </div>
    <div class="grow"></div>
    <span class="faint scanned">
      {#if data.scanning}Scanning…{:else if data.scannedAt}Scanned {ago(data.scannedAt, ui.now)}{/if}
    </span>
    <button class="btn sm" onclick={() => data.refresh(true)} disabled={data.scanning}><RefreshCw size={13} />Refresh</button>
  </div>

  <div class="cards">
    {#if !data.cards}
      {#each [1, 2, 3, 4, 5, 6] as k (k)}
        <div class="dcard card">
          <div class="skeleton" style="height:18px;width:50%"></div>
          <div class="skeleton" style="height:12px;width:80%;margin-top:12px"></div>
          <div class="skeleton" style="height:12px;width:60%;margin-top:8px"></div>
        </div>
      {/each}
    {:else}
      {#each data.cards as c (c.id)}
        {@const t = cur(c)}
        {@const Icon = iconFor(c.icon)}
        <div class="dcard card" class:missing={!t.exists}>
          <div class="top">
            <span class="ic"><Icon size={18} /></span>
            <div class="titles">
              <div class="name">{c.name}</div>
              {#if c.description}<div class="desc muted">{c.description}</div>{/if}
            </div>
            <button class="btn sm" disabled={!t.exists} onclick={() => open(t.path)} title={t.exists ? `Open ${t.path}` : 'Not created yet'}>
              <FolderOpen size={13} />Open folder
            </button>
          </div>
          {#if c.tabs.length > 1}
            <div class="tabs" role="tablist">
              {#each c.tabs as tb, i (tb.label)}
                <button
                  role="tab"
                  class="tab"
                  class:on={(tab[c.id] ?? 0) === i}
                  aria-selected={(tab[c.id] ?? 0) === i}
                  onclick={() => (tab = { ...tab, [c.id]: i })}
                >
                  {tb.label}
                  {#if tb.exists}<span class="faint">{tb.count}</span>{/if}
                </button>
              {/each}
            </div>
          {/if}
          <div class="path mono faint selectable" title={t.path}>{t.path}</div>
          {#if t.exists}
            <div class="stats">
              <span><strong>{t.count}</strong> {t.count === 1 ? 'item' : 'items'}</span>
              <span><strong>{bytes(t.totalBytes)}</strong></span>
              {#if t.newestName}
                <span class="newest" title={t.newestName}>newest <strong>{t.newestName}</strong> · {ago(t.newestMs, ui.now)}</span>
              {/if}
            </div>
            {#if t.entries.length}
              <button class="expander" onclick={() => (expanded = { ...expanded, [c.id]: !expanded[c.id] })} aria-expanded={!!expanded[c.id]}>
                {#if expanded[c.id]}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
                Newest {t.entries.length}
              </button>
              {#if t.entries.some((x) => x.action)}
                {@const lbl = t.entries.find((x) => x.action)?.action?.label}
                <span class="legend faint"><Play size={11} /> {lbl}</span>
              {/if}
              {#if expanded[c.id]}
                <ul class="entries">
                  {#each t.entries as e (e.path)}
                    <li>
                      <span class="eic">{#if e.isDir}<Folder size={14} />{:else}<File size={14} />{/if}</span>
                      <span class="ename mono" title={e.path}>{e.name}</span>
                      <span class="faint esz">{bytes(e.bytes)}</span>
                      <span class="faint eage">{ago(e.mtimeMs, ui.now)}</span>
                      {#if e.action}
                        <button class="act" onclick={() => act(e)} title={`${e.action.label}: ${e.action.target}`} aria-label={e.action.label}>
                          <Play size={13} />
                        </button>
                      {/if}
                      <button class="icon-btn" title={e.isDir ? 'Open folder' : 'Open with the default app'} aria-label="Open" onclick={() => run('Could not open it', api.openPath(e.path))}>
                        <ExternalLink size={14} />
                      </button>
                    </li>
                  {/each}
                </ul>
              {/if}
            {:else}
              <p class="faint emptyline">Empty.</p>
            {/if}
          {:else}
            <p class="faint emptyline">Not created yet — it appears once something writes here.</p>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .scroll {
    height: 100%;
    overflow: auto;
    padding: var(--s5);
  }
  .head {
    display: flex;
    align-items: flex-end;
    gap: var(--s3);
    margin-bottom: var(--s5);
  }
  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
  .head p {
    margin: 4px 0 0;
    font-size: 13px;
  }
  .grow {
    flex: 1;
  }
  .scanned {
    font-size: 12px;
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
    gap: var(--s4);
    align-items: start;
  }
  .dcard {
    padding: var(--s4);
    min-width: 0;
  }
  .dcard.missing .ic,
  .dcard.missing .name {
    opacity: 0.55;
  }
  .top {
    display: flex;
    align-items: flex-start;
    gap: var(--s3);
  }
  .ic {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: var(--accent-soft);
    color: var(--accent);
    flex: none;
  }
  .titles {
    flex: 1;
    min-width: 0;
  }
  .name {
    font-weight: 600;
  }
  .desc {
    font-size: 12.5px;
    margin-top: 1px;
  }
  .tabs {
    display: flex;
    gap: 4px;
    margin-top: var(--s3);
  }
  .tab {
    display: inline-flex;
    gap: 6px;
    height: 26px;
    padding: 0 10px;
    align-items: center;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: none;
    color: var(--muted);
    font-size: 12px;
    cursor: pointer;
  }
  .tab.on {
    background: var(--raised);
    color: var(--text);
    border-color: var(--border-strong);
  }
  .path {
    margin-top: var(--s3);
    font-size: 11.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stats {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin-top: var(--s2);
    font-size: 12.5px;
    color: var(--muted);
  }
  .stats strong {
    color: var(--text);
    font-weight: 500;
  }
  .newest {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .expander {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: var(--s3);
    padding: 2px 6px 2px 2px;
    border: 0;
    background: none;
    color: var(--muted);
    font-size: 12.5px;
    cursor: pointer;
    border-radius: 6px;
  }
  .expander:hover {
    color: var(--text);
  }
  .legend {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 6px;
    font-size: 12px;
  }
  .act {
    display: inline-grid;
    place-items: center;
    width: 28px;
    height: 24px;
    border-radius: 6px;
    border: 0;
    background: var(--accent-soft);
    color: var(--accent);
    cursor: pointer;
  }
  .act:hover {
    background: var(--accent);
    color: var(--accent-ink);
  }
  .entries {
    list-style: none;
    margin: 6px 0 0;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .entries li {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 5px 6px 5px 10px;
    border-bottom: 1px solid var(--border);
    font-size: 12.5px;
  }
  .entries li:last-child {
    border-bottom: 0;
  }
  .entries li:hover {
    background: var(--raised);
  }
  .eic {
    color: var(--faint);
    display: inline-grid;
  }
  .ename {
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 12px;
  }
  .esz {
    width: 64px;
    text-align: right;
    font-size: 12px;
  }
  .eage {
    width: 104px;
    text-align: right;
    font-size: 12px;
    white-space: nowrap;
  }
  .emptyline {
    margin: var(--s3) 0 0;
    font-size: 12.5px;
  }
</style>
