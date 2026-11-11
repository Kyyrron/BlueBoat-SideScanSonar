<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Rail from './lib/components/Rail.svelte';
  import TopBar from './lib/components/TopBar.svelte';
  import AppGrid from './lib/components/AppGrid.svelte';
  import BuildDrawer from './lib/components/BuildDrawer.svelte';
  import DataView from './lib/components/DataView.svelte';
  import BuildView from './lib/components/BuildView.svelte';
  import LogsView from './lib/components/LogsView.svelte';
  import SettingsView from './lib/components/SettingsView.svelte';
  import CommandPalette from './lib/components/CommandPalette.svelte';
  import ParamDialog from './lib/components/ParamDialog.svelte';
  import PackagePicker from './lib/components/PackagePicker.svelte';
  import ConfirmDialog from './lib/components/ConfirmDialog.svelte';
  import Toasts from './lib/components/Toasts.svelte';
  import { api, on } from './lib/ipc';
  import { exitText } from './lib/format';
  import { focusTerminal, retheme, setTerminalFontSize } from './lib/terminal';
  import { apps } from './lib/stores/apps.svelte';
  import { build } from './lib/stores/build.svelte';
  import { data, env } from './lib/stores/data.svelte';
  import { BUILD, displayName, sessions, stopSession } from './lib/stores/sessions.svelte';
  import { applyTheme, ui } from './lib/stores/ui.svelte';
  import type { BuildState, DataCard, ExitEvent, SessionView } from './lib/types';

  let collapseTimer: number | null = null;

  async function onQuitRequested() {
    const live = sessions.live;
    const n = live.length + (build.running ? 1 : 0);
    if (n === 0) {
      await api.quitHub();
      return;
    }
    const v = await ui.ask({
      title: 'Quit BlueBoat Hub?',
      body: `${n} ${n === 1 ? 'app keeps' : 'apps keep'} running in the background; the hub re-attaches next time.`,
      detail: live.map(displayName).join(', '),
      buttons: [
        { label: 'Cancel', value: 'cancel' },
        { label: 'Stop all and quit', value: 'stop' },
        { label: 'Quit hub', value: 'quit', kind: 'primary' },
      ],
      cancel: 'cancel',
    });
    if (v === 'quit') await api.quitHub();
    if (v === 'stop') {
      ui.quitWaiting = live.map((s) => s.name);
      for (const s of live) await stopSession(s.name);
      if (build.running) await build.cancel();
    }
  }

  // "Stop all and quit": quit once nothing runs any more
  $effect(() => {
    if (ui.quitWaiting && sessions.live.length === 0 && !build.running) {
      ui.quitWaiting = null;
      void api.quitHub();
    }
  });

  function onExit(ev: ExitEvent) {
    void apps.refresh();
    const crashed = !ev.expected && ((ev.exitCode ?? 0) !== 0 || ev.signal != null);
    if (ev.removed) {
      ui.toast('info', `${ev.appName}'s session ended`);
    } else if (crashed) {
      ui.toast('error', `${ev.appName} ${exitText(ev.exitCode, ev.signal)}`, 'Its last output stays in its card.');
    } else {
      ui.toast('info', `${ev.appName} closed`);
    }
  }

  function onBuild(st: BuildState) {
    const wasRunning = build.state?.running ?? false;
    build.state = st;
    if (st.running && !wasRunning) {
      ui.drawerOpen = true;
      if (collapseTimer) clearTimeout(collapseTimer);
    }
  }

  function onBuildFinished(st: BuildState) {
    build.state = st;
    void apps.refresh();
    void env.refresh();
    void build.loadPackages(true);
    if (st.ok) {
      ui.toast('success', `Build finished · ${st.packages.length} package${st.packages.length === 1 ? '' : 's'}`);
      if (collapseTimer) clearTimeout(collapseTimer);
      collapseTimer = window.setTimeout(() => {
        if (!build.running && build.state?.ok) ui.drawerOpen = false;
      }, 5000);
    } else {
      ui.drawerOpen = true;
      ui.toast('error', `Build failed${st.failed.length ? `: ${st.failed.join(', ')}` : ''}`, st.firstError ?? undefined);
    }
  }

  function liveTerminals(): SessionView[] {
    return sessions.apps;
  }

  async function onKey(e: KeyboardEvent) {
    if (!e.ctrlKey || e.altKey || e.metaKey) return;
    const k = e.key.toLowerCase();
    if (!e.shiftKey && k === 'k') {
      e.preventDefault();
      ui.paletteOpen = !ui.paletteOpen;
    } else if (!e.shiftKey && k === 'b') {
      e.preventDefault();
      void build.start([]);
    } else if (!e.shiftKey && /^[1-9]$/.test(k)) {
      const s = liveTerminals()[Number(k) - 1];
      if (s) {
        e.preventDefault();
        ui.view = 'apps';
        ui.maximize(s.name);
        await tick();
        setTimeout(() => focusTerminal(s.name), 260);
      }
    } else if (e.shiftKey && k === 'f') {
      e.preventDefault();
      const target = ui.maximized ?? ui.activeTerm ?? liveTerminals()[0]?.name ?? null;
      if (target) {
        if (target === BUILD) ui.drawerOpen = true;
        else {
          ui.view = 'apps';
          if (ui.collapsed[target]) ui.setCollapsed(target, false);
        }
        ui.searchOpen = target;
      }
    }
  }

  onMount(() => {
    applyTheme(ui.theme);
    setTerminalFontSize(ui.fontSize);
    const mq = matchMedia('(prefers-color-scheme: light)');
    const onScheme = () => requestAnimationFrame(retheme);
    mq.addEventListener('change', onScheme);

    const unsub = [
      on<SessionView[]>('sessions', (v) => sessions.apply(v)),
      on<BuildState>('build', onBuild),
      on<BuildState>('build-finished', onBuildFinished),
      on<DataCard[]>('data', (c) => data.set(c)),
      on<null>('config', () => void apps.refresh()),
      on<null>('env', () => {
        void env.refresh();
        void apps.refresh();
      }),
      on<ExitEvent>('app-exited', onExit),
      on<{ kind: 'info' | 'error'; text: string }>('toast', (t) => ui.toast(t.kind, t.text)),
      on<string[]>('quit-requested', () => void onQuitRequested()),
    ];

    void apps.refresh();
    void sessions.refresh();
    void build.refresh();
    void build.loadPackages();
    void data.refresh();
    void env.refresh();
    const envTimer = setInterval(() => void env.refresh(), 20_000);
    const appsTimer = setInterval(() => void apps.refresh(), 30_000);
    const onFocus = () => {
      ui.windowFocused = true;
      void env.refresh();
      void apps.refresh();
    };
    const onBlur = () => (ui.windowFocused = false);
    window.addEventListener('focus', onFocus);
    window.addEventListener('blur', onBlur);

    return () => {
      mq.removeEventListener('change', onScheme);
      clearInterval(envTimer);
      clearInterval(appsTimer);
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('blur', onBlur);
      for (const u of unsub) void u.then((f) => f());
    };
  });

  const toastBottom = $derived((ui.drawerOpen ? ui.drawerHeight : 40) + 16);
</script>

<svelte:window onkeydown={onKey} />

<div class="shell">
  <Rail />
  <div class="main">
    <TopBar />
    {#if ui.quitWaiting}
      <div class="quit-banner" role="status">
        <span>Stopping {sessions.live.length} {sessions.live.length === 1 ? 'app' : 'apps'} before quitting — answer any question they ask in their own windows.</span>
        <div class="grow"></div>
        <button class="btn sm" onclick={() => (ui.quitWaiting = null)}>Cancel quitting</button>
        <button class="btn sm primary" onclick={() => api.quitHub()}>Quit now, leave the rest running</button>
      </div>
    {/if}
    <main class="content">
      {#if ui.view === 'apps'}
        <AppGrid />
      {:else if ui.view === 'data'}
        <DataView />
      {:else if ui.view === 'build'}
        <BuildView />
      {:else if ui.view === 'logs'}
        <LogsView />
      {:else}
        <SettingsView />
      {/if}
    </main>
    <BuildDrawer />
  </div>
</div>

<ParamDialog />
<PackagePicker />
<CommandPalette />
<ConfirmDialog />
<Toasts bottom={toastBottom} />

<style>
  .shell {
    display: flex;
    height: 100%;
  }
  .main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .content {
    flex: 1;
    min-height: 0;
    position: relative;
  }
  .quit-banner {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 8px var(--s5);
    background: var(--warning-soft);
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  .grow {
    flex: 1;
  }
</style>
