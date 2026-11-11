<script lang="ts">
  import { Hammer, Pin, RefreshCw } from '@lucide/svelte';
  import { build } from '../stores/build.svelte';
  import { ui } from '../stores/ui.svelte';

  let picked = $state<Record<string, boolean>>({});
  const selected = $derived(build.packages.filter((p) => picked[p]));

  $effect(() => {
    if (ui.packagePickerOpen) void build.loadPackages();
  });

  function close() {
    ui.packagePickerOpen = false;
  }

  async function go() {
    const list = selected;
    close();
    await build.start(list);
  }

  function onKey(e: KeyboardEvent) {
    if (ui.packagePickerOpen && e.key === 'Escape') {
      e.stopPropagation();
      close();
    }
  }
</script>

<svelte:window onkeydown={onKey} />

{#if ui.packagePickerOpen}
  <div class="backdrop" role="presentation" onpointerdown={(e) => e.target === e.currentTarget && close()}>
    <div class="dialog card" role="dialog" aria-modal="true" aria-labelledby="pp-title">
      <div class="head">
        <h2 id="pp-title">Build selected packages</h2>
        <button class="icon-btn" title="Re-read the package list" aria-label="Refresh" onclick={() => build.loadPackages(true)}>
          <RefreshCw size={15} />
        </button>
      </div>
      <p class="muted sub">
        <span class="mono">colcon build --packages-select …</span> from the workspace. Interfaces first: every module's types
        resolve there.
      </p>
      {#if build.packagesError}
        <p class="err">{build.packagesError}</p>
      {/if}
      <div class="list">
        {#each build.packages as p, i (p)}
          <label class="row" class:pinned={i === 0 && p === 'blueboat_interfaces'}>
            <input type="checkbox" bind:checked={picked[p]} />
            <span class="mono name">{p}</span>
            {#if i === 0 && p === 'blueboat_interfaces'}<span class="badge"><Pin size={11} />build first</span>{/if}
          </label>
        {:else}
          {#each [1, 2, 3, 4] as k (k)}<div class="skeleton sk"></div>{/each}
        {/each}
      </div>
      <div class="actions">
        <button class="btn ghost" onclick={() => (picked = {})} disabled={!selected.length}>Clear</button>
        <div class="grow"></div>
        <button class="btn" onclick={close}>Cancel</button>
        <button class="btn primary" onclick={go} disabled={!selected.length}>
          <Hammer size={15} />Build {selected.length || ''}
          {selected.length === 1 ? 'package' : 'packages'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 95;
    display: grid;
    place-items: center;
    background: var(--overlay);
  }
  .dialog {
    width: min(520px, calc(100vw - 32px));
    padding: var(--s5);
    box-shadow: var(--shadow);
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
  }
  .sub {
    margin: var(--s2) 0 var(--s4);
    font-size: 13px;
  }
  .err {
    color: var(--error);
  }
  .list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    max-height: 46vh;
    overflow: auto;
    padding: 4px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--sunken);
  }
  .row {
    display: flex;
    align-items: center;
    gap: var(--s3);
    padding: 7px 10px;
    border-radius: 6px;
    cursor: pointer;
  }
  .row:hover {
    background: var(--raised);
  }
  .row.pinned {
    border-bottom: 1px dashed var(--border);
    margin-bottom: 4px;
  }
  .name {
    flex: 1;
    font-size: 13px;
  }
  input[type='checkbox'] {
    accent-color: var(--accent);
    width: 15px;
    height: 15px;
  }
  .sk {
    height: 28px;
    margin: 3px 4px;
  }
  .actions {
    display: flex;
    gap: var(--s2);
    margin-top: var(--s5);
  }
  .grow {
    flex: 1;
  }
</style>
