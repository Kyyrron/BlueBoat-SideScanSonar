<script lang="ts">
  import { TriangleAlert, CircleAlert } from '@lucide/svelte';
  import { ui } from '../stores/ui.svelte';

  const req = $derived(ui.confirm);
  let dialog: HTMLDivElement | undefined = $state();

  $effect(() => {
    if (req && dialog) {
      // focus the primary (non-cancel) action, never a danger one by default
      const btns = [...dialog.querySelectorAll<HTMLButtonElement>('button[data-kind]')];
      const pick = btns.find((b) => b.dataset.kind === 'primary') ?? btns[0];
      pick?.focus();
    }
  });

  function onKey(e: KeyboardEvent) {
    if (req && e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      req.resolve(req.cancel);
    }
  }
</script>

<svelte:window onkeydown={onKey} />

{#if req}
  <div class="backdrop" role="presentation" onpointerdown={(e) => e.target === e.currentTarget && req.resolve(req.cancel)}>
    <div class="dialog card" role="alertdialog" aria-modal="true" aria-labelledby="cd-title" bind:this={dialog}>
      <div class="head">
        {#if req.tone === 'danger'}
          <span class="tone danger"><CircleAlert size={20} /></span>
        {:else if req.tone === 'warning'}
          <span class="tone warning"><TriangleAlert size={20} /></span>
        {/if}
        <h2 id="cd-title">{req.title}</h2>
      </div>
      <p class="body">{req.body}</p>
      {#if req.detail}<p class="detail">{req.detail}</p>{/if}
      <div class="actions">
        {#each req.buttons as b (b.value)}
          <button
            class="btn"
            class:primary={b.kind === 'primary'}
            class:danger={b.kind === 'danger'}
            data-kind={b.kind ?? 'default'}
            onclick={() => req.resolve(b.value)}>{b.label}</button
          >
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: grid;
    place-items: center;
    background: var(--overlay);
    animation: fade var(--t-fast) var(--ease);
  }
  @keyframes fade {
    from {
      opacity: 0;
    }
  }
  .dialog {
    width: min(520px, calc(100vw - 32px));
    padding: var(--s5);
    box-shadow: var(--shadow);
    animation: rise var(--t-med) var(--ease);
  }
  @keyframes rise {
    from {
      transform: translateY(8px) scale(0.98);
      opacity: 0;
    }
  }
  .head {
    display: flex;
    align-items: center;
    gap: var(--s3);
  }
  h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
  }
  .tone {
    display: inline-grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 10px;
    flex: none;
  }
  .tone.danger {
    color: var(--error);
    background: var(--error-soft);
  }
  .tone.warning {
    color: var(--warning);
    background: var(--warning-soft);
  }
  .body {
    margin: var(--s4) 0 0;
    color: var(--text);
    white-space: pre-line;
    line-height: 1.55;
  }
  .detail {
    margin: var(--s2) 0 0;
    color: var(--muted);
    font-size: 13px;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--s2);
    margin-top: var(--s5);
  }
</style>
