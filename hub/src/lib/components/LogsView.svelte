<script lang="ts">
  import { ExternalLink, FolderOpen, RefreshCw } from '@lucide/svelte';
  import { api, errText } from '../ipc';
  import { ago, bytes } from '../format';
  import { apps } from '../stores/apps.svelte';
  import { env } from '../stores/data.svelte';
  import { run } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';
  import type { LogFile } from '../types';

  let logs = $state<LogFile[] | null>(null);

  async function load() {
    try {
      logs = await api.listLogs();
    } catch (e) {
      ui.toast('error', 'Could not list the logs', errText(e));
    }
  }

  $effect(() => {
    void load();
  });

  const grouped = $derived.by(() => {
    const m = new Map<string, LogFile[]>();
    for (const l of logs ?? []) m.set(l.app, [...(m.get(l.app) ?? []), l]);
    return [...m.entries()];
  });

  const label = (id: string) => (id === 'build' ? 'Build' : (apps.byId(id)?.name ?? id));
</script>

<div class="scroll">
  <div class="head">
    <div>
      <h2>Logs</h2>
      <p class="muted">
        Every session's output, written by tmux as it happens. The newest 20 per app are kept in
        <span class="mono">{env.view?.logsDir ?? '~/.local/state/blueboat-hub/logs'}</span>.
      </p>
    </div>
    <div class="grow"></div>
    <button class="btn sm" onclick={load}><RefreshCw size={13} />Refresh</button>
    {#if env.view}
      <button class="btn sm" onclick={() => env.view && run('Could not open the folder', api.openPath(env.view.logsDir))}>
        <FolderOpen size={13} />Open folder
      </button>
    {/if}
  </div>

  {#if logs && !logs.length}
    <p class="muted">No logs yet — launch an app and its output lands here.</p>
  {/if}

  <div class="groups">
    {#each grouped as [app, list] (app)}
      <div class="card panel">
        <div class="ph"><span class="section-title">{label(app)}</span><span class="faint">{list.length}</span></div>
        <ul>
          {#each list as l (l.path)}
            <li>
              <span class="mono nm" title={l.path}>{l.name}</span>
              <span class="faint sz">{bytes(l.bytes)}</span>
              <span class="faint age">{ago(l.mtimeMs, ui.now)}</span>
              <button class="icon-btn" aria-label="Open log" title="Open with the default text viewer" onclick={() => run('Could not open the log', api.openPath(l.path))}>
                <ExternalLink size={14} />
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {/each}
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
    gap: var(--s2);
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
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
    gap: var(--s4);
    align-items: start;
  }
  .panel {
    padding: var(--s4);
  }
  .ph {
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--s2);
    font-size: 12px;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  li {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
    font-size: 12.5px;
  }
  li:last-child {
    border-bottom: 0;
  }
  .nm {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sz {
    width: 70px;
    text-align: right;
  }
  .age {
    width: 110px;
    text-align: right;
    white-space: nowrap;
  }
</style>
