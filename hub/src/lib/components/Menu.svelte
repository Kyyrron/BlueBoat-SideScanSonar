<script lang="ts" module>
  import type { Component } from 'svelte';

  export interface MenuItem {
    label: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon?: Component<any>;
    action?: () => void;
    disabled?: boolean;
    danger?: boolean;
    hint?: string;
    separator?: boolean;
  }
</script>

<script lang="ts">
  import { Ellipsis } from '@lucide/svelte';
  import type { Snippet } from 'svelte';

  let {
    items,
    label = 'More actions',
    align = 'right',
    trigger,
  }: {
    items: MenuItem[];
    label?: string;
    align?: 'left' | 'right';
    trigger?: Snippet;
  } = $props();

  let open = $state(false);
  let root: HTMLDivElement | undefined = $state();

  function onWindowPointer(e: PointerEvent) {
    if (open && root && !root.contains(e.target as Node)) open = false;
  }

  function onKey(e: KeyboardEvent) {
    if (open && e.key === 'Escape') {
      e.stopPropagation();
      open = false;
    }
  }

  function pick(item: MenuItem) {
    if (item.disabled) return;
    open = false;
    item.action?.();
  }
</script>

<svelte:window onpointerdown={onWindowPointer} onkeydown={onKey} />

<div class="menu-root" bind:this={root}>
  <button
    class={trigger ? 'trigger' : 'icon-btn'}
    aria-label={label}
    title={label}
    aria-haspopup="menu"
    aria-expanded={open}
    onclick={() => (open = !open)}
  >
    {#if trigger}{@render trigger()}{:else}<Ellipsis size={16} />{/if}
  </button>
  {#if open}
    <div class="menu" class:left={align === 'left'} role="menu">
      {#each items as item, i (i)}
        {#if item.separator}
          <div class="sep" role="separator"></div>
        {:else}
          <button
            role="menuitem"
            class="item"
            class:danger={item.danger}
            disabled={item.disabled}
            title={item.hint}
            onclick={() => pick(item)}
          >
            <span class="ic">
              {#if item.icon}<item.icon size={15} />{/if}
            </span>
            <span class="lbl">{item.label}</span>
          </button>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<style>
  .menu-root {
    position: relative;
    display: inline-flex;
  }
  .trigger {
    display: inline-flex;
    align-items: center;
    background: none;
    border: 0;
    padding: 0;
    cursor: pointer;
  }
  .menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    z-index: 60;
    min-width: 220px;
    max-width: 340px;
    padding: 6px;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    box-shadow: var(--shadow);
    animation: pop var(--t-fast) var(--ease);
  }
  .menu.left {
    left: 0;
    right: auto;
  }
  @keyframes pop {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
  }
  .item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 7px 10px;
    border: 0;
    border-radius: 6px;
    background: none;
    text-align: left;
    font-size: 13px;
    cursor: pointer;
    color: var(--text);
  }
  .item:hover:not(:disabled) {
    background: var(--raised);
  }
  .item:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .item.danger {
    color: var(--error);
  }
  .ic {
    width: 16px;
    display: inline-grid;
    place-items: center;
    color: var(--muted);
  }
  .item.danger .ic {
    color: var(--error);
  }
  .lbl {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sep {
    height: 1px;
    margin: 5px 4px;
    background: var(--border);
  }
</style>
