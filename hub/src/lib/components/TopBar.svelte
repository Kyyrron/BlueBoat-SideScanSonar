<script lang="ts">
  import { ChevronDown, Command, GitBranch, Hammer, ListChecks, Square } from '@lucide/svelte';
  import Menu from './Menu.svelte';
  import { build } from '../stores/build.svelte';
  import { env } from '../stores/data.svelte';
  import { ui } from '../stores/ui.svelte';
  import { ago, duration } from '../format';

  const e = $derived(env.view);
  const b = $derived(build.state);

  // Install pill: the last hub build if there is one, else install/setup.bash's age.
  const install = $derived.by(() => {
    if (b?.running) {
      const cur = b.packages.find((p) => p.status === 'building');
      return {
        tone: 'warn',
        text: `Building ${build.done}/${b.expected || '?'}${cur ? ` · ${cur.name}` : ''}`,
        title: 'colcon build is running — open the build drawer',
      };
    }
    if (b?.finishedMs) {
      if (b.ok) {
        return {
          tone: 'ok',
          text: `Built ${ago(b.finishedMs, ui.now)} · ${b.packages.length} package${b.packages.length === 1 ? '' : 's'}`,
          title: `Last hub build took ${duration(b.finishedMs - b.startedMs)}`,
        };
      }
      return {
        tone: 'err',
        text: `Build failed: ${b.failed.length ? b.failed.join(', ') : 'see log'}`,
        title: b.firstError ?? 'The last build failed',
      };
    }
    if (e?.install.ms) {
      return { tone: 'ok', text: `install: built ${ago(e.install.ms, ui.now)}`, title: e.install.detail };
    }
    if (e && !e.install.ok) return { tone: 'err', text: 'not built', title: e.install.detail };
    return { tone: '', text: 'install …', title: '' };
  });

  const subs = $derived(e?.git.modifiedSubmodules.length ?? 0);
</script>

<header class="topbar">
  <h1>BlueBoat Hub</h1>
  <div class="pills">
    <span class="pill" title={e?.ros.detail ?? ''}>
      <span class="dot" class:ok={e?.ros.ok} class:err={e && !e.ros.ok}></span>{e?.ros.label ?? 'ROS …'}
    </span>
    <span class="pill" title={e?.venv.detail ?? ''}>
      <span class="dot" class:ok={e?.venv.ok} class:err={e && !e.venv.ok}></span>venv
    </span>
    <button class="pill as-btn" title={install.title} onclick={() => (ui.drawerOpen = true)}>
      <span
        class="dot"
        class:ok={install.tone === 'ok'}
        class:warn={install.tone === 'warn'}
        class:err={install.tone === 'err'}
      ></span>{install.text}
    </button>
    {#if e?.git.branch}
      <span
        class="pill"
        title={subs
          ? `Modified submodules: ${e.git.modifiedSubmodules.join(', ')} (read-only view of git status)`
          : 'Superproject branch (read-only view of git status)'}
      >
        <GitBranch size={13} />{e.git.branch}{#if subs}<span class="sep">·</span>{subs} submodule{subs === 1 ? '' : 's'} modified{/if}
      </span>
    {/if}
  </div>
  <div class="grow"></div>
  <div class="split">
    {#if build.running}
      <button class="btn main" onclick={() => (ui.drawerOpen = true)} title="Show the running build">
        <span class="spinner" aria-hidden="true"></span>Building…
      </button>
    {:else}
      <button class="btn primary main" onclick={() => build.start([])} title="colcon build (Ctrl+B)">
        <Hammer size={15} />Build
      </button>
    {/if}
    <Menu
      label="Build options"
      items={[
        { label: 'Build all packages', icon: Hammer, action: () => build.start([]), disabled: build.running },
        {
          label: 'Select packages…',
          icon: ListChecks,
          action: () => (ui.packagePickerOpen = true),
          disabled: build.running,
        },
        { separator: true, label: '' },
        { label: 'Cancel build', icon: Square, action: () => build.cancel(), disabled: !build.running, danger: true },
      ]}
    >
      {#snippet trigger()}
        <span class="btn chev" class:primary={!build.running}><ChevronDown size={15} /></span>
      {/snippet}
    </Menu>
  </div>
  <button class="btn palette" onclick={() => (ui.paletteOpen = true)} title="Command palette">
    <Command size={14} /><span>Search actions</span><kbd>Ctrl K</kbd>
  </button>
</header>

<style>
  .topbar {
    height: var(--topbar-h);
    flex: none;
    display: flex;
    align-items: center;
    gap: var(--s3);
    padding: 0 var(--s5) 0 var(--s5);
    border-bottom: 1px solid var(--border);
    background: var(--bg);
  }
  h1 {
    margin: 0 var(--s2) 0 0;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: -0.01em;
    white-space: nowrap;
  }
  .pills {
    display: flex;
    gap: var(--s2);
    min-width: 0;
    overflow: hidden;
  }
  .as-btn {
    cursor: pointer;
  }
  .as-btn:hover {
    border-color: var(--border-strong);
    color: var(--text);
  }
  .sep {
    margin: 0 2px;
    color: var(--faint);
  }
  .grow {
    flex: 1;
  }
  .split {
    display: inline-flex;
    align-items: center;
  }
  .split .main {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
  }
  .chev {
    width: 30px;
    padding: 0;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    margin-left: 1px;
  }
  .palette {
    color: var(--muted);
    background: var(--surface);
    border-color: var(--border);
  }
  .palette span {
    font-weight: 400;
  }
  .spinner {
    width: 13px;
    height: 13px;
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
  @media (max-width: 1440px) {
    .palette span {
      display: none;
    }
  }
</style>
