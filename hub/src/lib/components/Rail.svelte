<script lang="ts">
  import { FolderOpen, Hammer, LayoutGrid, ScrollText, Settings, Terminal } from '@lucide/svelte';
  import { build } from '../stores/build.svelte';
  import { sessions } from '../stores/sessions.svelte';
  import { ui, type View } from '../stores/ui.svelte';

  const items: { id: View; label: string; icon: typeof LayoutGrid }[] = [
    { id: 'apps', label: 'Apps', icon: LayoutGrid },
    { id: 'data', label: 'Data', icon: FolderOpen },
    { id: 'build', label: 'Build', icon: Hammer },
    { id: 'logs', label: 'Logs', icon: ScrollText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const running = $derived(sessions.live.length);
</script>

<nav class="rail" aria-label="Views">
  <div class="logo" title="BlueBoat Hub">
    <svg viewBox="0 0 512 512" width="30" height="30" aria-hidden="true">
      <g fill="none" stroke="var(--accent)" stroke-linecap="round">
        <path d="M256 236 C 200 268, 150 318, 118 384" stroke-width="30" />
        <path d="M256 236 C 312 268, 362 318, 394 384" stroke-width="30" />
        <path d="M256 236 C 216 292, 196 346, 190 404" stroke-width="22" opacity="0.5" />
        <path d="M256 236 C 296 292, 316 346, 322 404" stroke-width="22" opacity="0.5" />
      </g>
      <path d="M150 196 L362 196 L334 236 L178 236 Z" fill="var(--text)" />
      <rect x="236" y="150" width="40" height="46" rx="8" fill="var(--text)" />
    </svg>
  </div>
  {#each items as it (it.id)}
    <button
      class="item"
      class:active={ui.view === it.id}
      aria-current={ui.view === it.id ? 'page' : undefined}
      title={it.label}
      aria-label={it.label}
      onclick={() => (ui.view = it.id)}
    >
      <it.icon size={20} />
      {#if it.id === 'build' && build.running}<span class="spin-dot" aria-hidden="true"></span>{/if}
    </button>
  {/each}
  <div class="grow"></div>
  <button
    class="running"
    title={running ? `${running} app${running === 1 ? '' : 's'} running` : 'Nothing running'}
    aria-label="Running apps"
    onclick={() => (ui.view = 'apps')}
  >
    <Terminal size={18} />
    {#if running}<span class="count">{running}</span>{/if}
  </button>
</nav>

<style>
  .rail {
    width: var(--rail-w);
    flex: none;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 12px 0 14px;
    background: var(--surface);
    border-right: 1px solid var(--border);
  }
  .logo {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    margin-bottom: 10px;
  }
  .item,
  .running {
    position: relative;
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 10px;
    border: 0;
    background: none;
    color: var(--muted);
    cursor: pointer;
    transition:
      background var(--t-fast) var(--ease),
      color var(--t-fast) var(--ease);
  }
  .item:hover,
  .running:hover {
    background: var(--raised);
    color: var(--text);
  }
  .item.active {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .item.active::before {
    content: '';
    position: absolute;
    left: -11px;
    top: 10px;
    bottom: 10px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: var(--accent);
  }
  .grow {
    flex: 1;
  }
  .count {
    position: absolute;
    top: 3px;
    right: 2px;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 9px;
    background: var(--running);
    color: #04140a;
    font-size: 11px;
    font-weight: 700;
    line-height: 18px;
    text-align: center;
  }
  .spin-dot {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--warning);
    animation: blink 1s ease-in-out infinite;
  }
  @keyframes blink {
    50% {
      opacity: 0.3;
    }
  }
</style>
