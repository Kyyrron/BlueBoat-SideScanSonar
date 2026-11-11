<script lang="ts">
  import { ChevronDown, ChevronUp, CircleCheck, CircleX, FileText, Hammer, Square } from '@lucide/svelte';
  import { api } from '../ipc';
  import { ago, duration } from '../format';
  import { terminal } from '../terminal';
  import { build } from '../stores/build.svelte';
  import { BUILD, run, sessions } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';

  const b = $derived(build.state);
  const s = $derived(sessions.build);
  const open = $derived(ui.drawerOpen);

  const summary = $derived.by(() => {
    if (!b || (!b.running && !b.finishedMs)) return { tone: '', text: 'No build from the hub yet' };
    if (b.running) {
      const cur = b.packages.filter((p) => p.status === 'building').map((p) => p.name);
      return {
        tone: 'warn',
        text: `Building ${build.done}/${b.expected || '?'}${cur.length ? ` · ${cur.join(', ')}` : ''} · ${duration(ui.now - b.startedMs)}`,
      };
    }
    const n = b.packages.filter((p) => p.status === 'finished').length;
    const took = b.finishedMs ? duration(b.finishedMs - b.startedMs) : '';
    if (b.ok) return { tone: 'ok', text: `Last build ✓ ${n}/${b.expected || b.packages.length} · ${took} · ${ago(b.finishedMs, ui.now)}` };
    return {
      tone: 'err',
      text: `Last build failed${b.failed.length ? `: ${b.failed.join(', ')}` : ''} · ${took} · ${ago(b.finishedMs, ui.now)}`,
    };
  });

  // drag to resize
  let dragging = $state(false);
  function startDrag(e: PointerEvent) {
    dragging = true;
    const startY = e.clientY;
    const startH = ui.drawerHeight;
    const move = (ev: PointerEvent) => {
      const h = Math.max(160, Math.min(window.innerHeight - 200, startH + (startY - ev.clientY)));
      ui.drawerHeight = h;
    };
    const up = () => {
      dragging = false;
      ui.setDrawerHeight(ui.drawerHeight);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }
</script>

<div class="drawer" class:open class:dragging style:height={open ? `${ui.drawerHeight}px` : undefined}>
  {#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="handle" onpointerdown={startDrag} title="Drag to resize"></div>
  {/if}
  <div class="bar">
    <button class="toggle" onclick={() => (ui.drawerOpen = !open)} aria-expanded={open} aria-controls="build-drawer-body">
      {#if open}<ChevronDown size={15} />{:else}<ChevronUp size={15} />{/if}
      <Hammer size={14} />
      <span class="lbl">Build</span>
    </button>
    <span class="sum" class:ok={summary.tone === 'ok'} class:warn={summary.tone === 'warn'} class:err={summary.tone === 'err'}>
      {#if summary.tone === 'ok'}<CircleCheck size={14} />{:else if summary.tone === 'err'}<CircleX size={14} />{:else if summary.tone === 'warn'}<span class="spinner"></span>{/if}
      {summary.text}
    </span>
    {#if b && b.packages.length}
      <div class="strip" aria-label="Package progress">
        {#each b.packages as p (p.name)}
          <span
            class="chip {p.status}"
            title={`${p.name}: ${p.status}${p.seconds != null ? ` (${p.seconds.toFixed(1)} s)` : ''}`}
          >{p.name}</span>
        {/each}
        {#if b.running && b.expected > b.packages.length}
          {#each Array(Math.min(b.expected - b.packages.length, 12)) as _, i (i)}<span class="chip pending"></span>{/each}
        {/if}
      </div>
    {:else}
      <div class="grow"></div>
    {/if}
    {#if b?.running}
      <button class="btn sm danger-ghost" onclick={() => build.cancel()} title="Ctrl-C to colcon: it aborts running jobs and prints its summary">
        <Square size={12} />Cancel
      </button>
    {/if}
    {#if s?.log}
      <button class="btn sm ghost" onclick={() => s?.log && run('Could not open the log', api.openPath(s.log))}><FileText size={13} />Log</button>
    {/if}
    <button class="btn sm ghost" onclick={() => (ui.drawerOpen = !open)}>{open ? 'Hide' : 'Open'}</button>
  </div>
  {#if open}
    <div class="body" id="build-drawer-body">
      {#if b?.ok === false && b.firstError && !b.running}
        <div class="first-error mono selectable" title="First error line of the failed package">
          <CircleX size={14} /><span>{b.firstError}</span>
        </div>
      {/if}
      {#if s}
        <div class="term" use:terminal={BUILD}></div>
      {:else}
        <div class="empty muted">
          {#if b?.finishedMs}
            The build session was dismissed; its full output is in the log under <span class="mono">~/.local/state/blueboat-hub/logs/</span>.
          {:else}
            Builds run <span class="mono">colcon build</span> from the workspace in their own terminal, shown here.
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .drawer {
    position: relative;
    flex: none;
    display: flex;
    flex-direction: column;
    border-top: 1px solid var(--border);
    background: var(--surface);
    transition: height var(--t-med) var(--ease);
  }
  .drawer.dragging {
    transition: none;
  }
  .handle {
    position: absolute;
    top: -4px;
    left: 0;
    right: 0;
    height: 8px;
    cursor: ns-resize;
    z-index: 3;
  }
  .bar {
    display: flex;
    align-items: center;
    gap: var(--s3);
    height: 40px;
    flex: none;
    padding: 0 var(--s3) 0 var(--s2);
    min-width: 0;
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 8px;
    border: 0;
    border-radius: 6px;
    background: none;
    color: var(--muted);
    cursor: pointer;
  }
  .toggle:hover {
    background: var(--raised);
    color: var(--text);
  }
  .lbl {
    font-weight: 600;
    color: var(--text);
    font-size: 13px;
  }
  .sum {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: none;
    max-width: 46%;
  }
  .sum.ok {
    color: var(--running);
  }
  .sum.err {
    color: var(--error);
  }
  .sum.warn {
    color: var(--warning);
  }
  .strip {
    display: flex;
    gap: 4px;
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }
  .grow {
    flex: 1;
  }
  .chip {
    flex: none;
    height: 20px;
    min-width: 18px;
    padding: 0 7px;
    border-radius: 5px;
    font-size: 11px;
    line-height: 20px;
    font-family: var(--font-mono);
    background: var(--raised);
    color: var(--muted);
    white-space: nowrap;
  }
  .chip.building {
    color: var(--warning);
    background: var(--warning-soft);
    animation: breathe 1.4s ease-in-out infinite;
  }
  .chip.finished {
    color: var(--running);
    background: var(--running-soft);
  }
  .chip.failed {
    color: #fff;
    background: var(--error);
  }
  .chip.aborted {
    color: var(--error);
    background: var(--error-soft);
    text-decoration: line-through;
  }
  .chip.pending {
    width: 18px;
    padding: 0;
    border: 1px dashed var(--border-strong);
    background: none;
  }
  @keyframes breathe {
    50% {
      opacity: 0.55;
    }
  }
  .body {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border-top: 1px solid var(--border);
  }
  .first-error {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    font-size: 12px;
    color: var(--error);
    background: var(--error-soft);
    border-bottom: 1px solid var(--border);
  }
  .first-error span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .term {
    position: relative;
    flex: 1;
    min-height: 0;
  }
  .empty {
    padding: var(--s5);
    font-size: 13px;
  }
  .spinner {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--border-strong);
    border-top-color: var(--warning);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
