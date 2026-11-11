<script lang="ts">
  import { Hammer, ListChecks, PanelBottomOpen, RefreshCw } from '@lucide/svelte';
  import { ago, duration } from '../format';
  import { build } from '../stores/build.svelte';
  import { ui } from '../stores/ui.svelte';

  const b = $derived(build.state);

  $effect(() => {
    void build.loadPackages();
  });

  const statusOf = (name: string) => b?.packages.find((p) => p.name === name);
</script>

<div class="scroll">
  <div class="head">
    <div>
      <h2>Build</h2>
      <p class="muted">
        <span class="mono">source /opt/ros/jazzy/setup.bash && colcon build</span> from the workspace, in its own terminal. Running
        apps keep the old install until restarted; the hub never stops them for a build.
      </p>
    </div>
  </div>

  <div class="actions">
    <button class="btn primary" onclick={() => build.start([])} disabled={build.running}><Hammer size={15} />Build all packages</button>
    <button class="btn" onclick={() => (ui.packagePickerOpen = true)} disabled={build.running}><ListChecks size={15} />Select packages…</button>
    <button class="btn ghost" onclick={() => (ui.drawerOpen = true)}><PanelBottomOpen size={15} />Show build terminal</button>
  </div>

  <div class="grid">
    <div class="card panel">
      <div class="ph">
        <span class="section-title">Packages</span>
        <button class="icon-btn" title="Re-read with colcon list" aria-label="Refresh" onclick={() => build.loadPackages(true)}><RefreshCw size={14} /></button>
      </div>
      {#if build.packagesError}<p class="err">{build.packagesError}</p>{/if}
      <ul class="pkgs">
        {#each build.packages as p, i (p)}
          {@const st = statusOf(p)}
          <li>
            <span class="mono">{p}</span>
            {#if i === 0 && p === 'blueboat_interfaces'}<span class="badge">build first</span>{/if}
            <span class="grow"></span>
            {#if st}
              <span class="badge {st.status === 'finished' ? 'ok' : st.status === 'building' ? 'warn' : 'err'}">
                {st.status}{st.seconds != null ? ` · ${st.seconds.toFixed(1)} s` : ''}
              </span>
            {/if}
            <button class="btn sm ghost" disabled={build.running} onclick={() => build.start([p])}>Build</button>
          </li>
        {/each}
      </ul>
    </div>

    <div class="card panel">
      <div class="ph"><span class="section-title">Last build</span></div>
      {#if b && (b.running || b.finishedMs)}
        <dl>
          <dt>Started</dt>
          <dd>{ago(b.startedMs, ui.now)}</dd>
          <dt>Scope</dt>
          <dd>{b.selection.length ? b.selection.join(', ') : 'all packages'}</dd>
          <dt>Result</dt>
          <dd>
            {#if b.running}<span class="warn">running · {duration(ui.now - b.startedMs)}</span>
            {:else if b.ok}<span class="ok">succeeded in {duration((b.finishedMs ?? 0) - b.startedMs)}</span>
            {:else}<span class="err">failed{b.failed.length ? `: ${b.failed.join(', ')}` : ''}</span>{/if}
          </dd>
          {#if b.firstError && !b.ok && !b.running}
            <dt>First error</dt>
            <dd class="mono selectable errline">{b.firstError}</dd>
          {/if}
        </dl>
        {#if b.summary.length}
          <pre class="summary mono selectable">{b.summary.join('\n')}</pre>
        {/if}
      {:else}
        <p class="muted">No build has run from the hub yet.</p>
      {/if}
    </div>
  </div>
</div>

<style>
  .scroll {
    height: 100%;
    overflow: auto;
    padding: var(--s5);
  }
  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
  .head p {
    margin: 4px 0 0;
    font-size: 13px;
    max-width: 900px;
  }
  .actions {
    display: flex;
    gap: var(--s2);
    margin: var(--s4) 0 var(--s5);
  }
  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--s4);
    align-items: start;
  }
  .panel {
    padding: var(--s4);
  }
  .ph {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--s3);
  }
  .pkgs {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .pkgs li {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 6px 4px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .pkgs li:last-child {
    border-bottom: 0;
  }
  .grow {
    flex: 1;
  }
  dl {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 8px 12px;
    margin: 0;
    font-size: 13px;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .ok {
    color: var(--running);
  }
  .warn {
    color: var(--warning);
  }
  .err,
  .errline {
    color: var(--error);
  }
  .summary {
    margin: var(--s4) 0 0;
    padding: var(--s3);
    border-radius: 8px;
    background: var(--term-bg);
    color: var(--term-fg);
    white-space: pre-wrap;
  }
</style>
