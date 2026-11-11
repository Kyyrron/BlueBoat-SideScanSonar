<script lang="ts">
  import { CircleCheck, CircleX, Info, TriangleAlert, X } from '@lucide/svelte';
  import { ui } from '../stores/ui.svelte';

  let { bottom = 16 }: { bottom?: number } = $props();
</script>

<div class="stack" style:bottom="{bottom}px" aria-live="polite">
  {#each ui.toasts as t (t.id)}
    <div class="toast card {t.kind}" role="status">
      <span class="ic">
        {#if t.kind === 'success'}<CircleCheck size={18} />
        {:else if t.kind === 'error'}<CircleX size={18} />
        {:else if t.kind === 'warning'}<TriangleAlert size={18} />
        {:else}<Info size={18} />{/if}
      </span>
      <div class="txt">
        <div class="t">{t.text}</div>
        {#if t.detail}<div class="d selectable">{t.detail}</div>{/if}
      </div>
      <button class="icon-btn" aria-label="Dismiss" onclick={() => ui.dismissToast(t.id)}><X size={14} /></button>
    </div>
  {/each}
</div>

<style>
  .stack {
    position: fixed;
    right: 16px;
    z-index: 90;
    display: flex;
    flex-direction: column;
    gap: var(--s2);
    width: min(400px, calc(100vw - 32px));
    pointer-events: none;
    transition: bottom var(--t-med) var(--ease);
  }
  .toast {
    pointer-events: auto;
    display: flex;
    align-items: flex-start;
    gap: var(--s3);
    padding: var(--s3) var(--s3) var(--s3) var(--s4);
    box-shadow: var(--shadow);
    border-left: 3px solid var(--info);
    animation: slide var(--t-med) var(--ease);
  }
  @keyframes slide {
    from {
      transform: translateX(16px);
      opacity: 0;
    }
  }
  .toast.success {
    border-left-color: var(--running);
  }
  .toast.error {
    border-left-color: var(--error);
  }
  .toast.warning {
    border-left-color: var(--warning);
  }
  .ic {
    margin-top: 1px;
    color: var(--info);
  }
  .success .ic {
    color: var(--running);
  }
  .error .ic {
    color: var(--error);
  }
  .warning .ic {
    color: var(--warning);
  }
  .txt {
    flex: 1;
    min-width: 0;
  }
  .t {
    font-weight: 500;
  }
  .d {
    margin-top: 2px;
    color: var(--muted);
    font-size: 12.5px;
    overflow-wrap: anywhere;
  }
</style>
