// Live tmux sessions (apps and the build), pushed by the Rust tick.

import { api, errText } from '../ipc';
import type { LaunchOutcome, SessionView } from '../types';
import { disposeTerminal } from '../terminal';
import { apps } from './apps.svelte';
import { morph, ui } from './ui.svelte';

export const BUILD = 'build';

class Sessions {
  list = $state<SessionView[]>([]);

  apply(next: SessionView[]) {
    const before = new Set(this.list.map((s) => s.name));
    const after = new Set(next.map((s) => s.name));
    const shapeChanged =
      before.size !== after.size ||
      [...after].some((n) => !before.has(n)) ||
      this.list.some((s) => {
        const n = next.find((x) => x.name === s.name);
        return n != null && (n.state === 'exited') !== (s.state === 'exited');
      });
    for (const gone of before) {
      if (!after.has(gone)) {
        disposeTerminal(gone);
        if (ui.maximized === gone) ui.maximized = null;
      }
    }
    if (shapeChanged) morph(() => void (this.list = next));
    else this.list = next;
  }

  get apps(): SessionView[] {
    return this.list.filter((s) => s.app !== BUILD);
  }

  get live(): SessionView[] {
    return this.apps.filter((s) => s.state !== 'exited');
  }

  get build(): SessionView | undefined {
    return this.list.find((s) => s.name === BUILD);
  }

  get(name: string): SessionView | undefined {
    return this.list.find((s) => s.name === name);
  }

  forApp(id: string): SessionView[] {
    return this.list.filter((s) => s.app === id);
  }

  async refresh() {
    try {
      this.apply(await api.sessions());
    } catch {
      /* the next tick event brings it */
    }
  }
}

export const sessions = new Sessions();

export function displayName(s: SessionView): string {
  const a = apps.byId(s.app);
  const base = a?.name ?? s.app;
  const m = /-(\d+)$/.exec(s.name);
  return m && a && !a.singleton ? `${base} #${m[1]}` : base;
}

/** Launch an app; opens the parameter dialog when it needs input. */
export async function launchApp(
  id: string,
  opts: { variant?: string | null; params?: Record<string, string>; ask?: boolean } = {},
) {
  const app = apps.byId(id);
  if (!app) return;
  if (!app.available) {
    ui.toast('warning', `${app.name} can't start`, app.reason ?? undefined);
    return;
  }
  const needsInput = app.params.some((p) => !p.optional && !p.default && !(opts.params ?? {})[p.name]);
  if (opts.ask || needsInput) {
    ui.params = { app: id, variant: opts.variant ?? null, initial: opts.params ?? app.lastRun?.params ?? {} };
    return;
  }
  await doLaunch(id, opts.params ?? {}, opts.variant ?? null);
}

export async function doLaunch(id: string, params: Record<string, string>, variant: string | null): Promise<boolean> {
  const app = apps.byId(id);
  try {
    const out: LaunchOutcome = await api.launch(id, params, variant);
    if (out.outcome === 'alreadyRunning') {
      ui.toast(
        'info',
        `${app?.name ?? id} is already running`,
        out.focused ? 'Its window was brought forward.' : 'It has no window to bring forward.',
      );
    }
    void apps.refresh();
    return true;
  } catch (e) {
    ui.toast('error', `${app?.name ?? id} did not start`, errText(e));
    return false;
  }
}

export async function stopSession(name: string) {
  try {
    await api.stop(name);
  } catch (e) {
    ui.toast('error', 'Stop failed', errText(e));
  }
}

export async function forceStop(name: string) {
  const s = sessions.get(name);
  if (!s) return;
  const app = apps.byId(s.app);
  const sent = ui.ctrlCSent[name];
  if (!sent) {
    const v = await ui.ask({
      title: `Force-stop ${displayName(s)}?`,
      body: app?.forceWarning ?? 'This skips the app’s own close handling.',
      detail: 'Step 1 sends Ctrl-C to the app. If it still runs, a second step can end its tmux session.',
      tone: 'danger',
      buttons: [
        { label: 'Cancel', value: 'cancel' },
        { label: 'Send Ctrl-C', value: 'ctrlc', kind: 'danger' },
      ],
      cancel: 'cancel',
    });
    if (v !== 'ctrlc') return;
    try {
      await api.forceStop(name, false);
      ui.ctrlCSent = { ...ui.ctrlCSent, [name]: Date.now() };
    } catch (e) {
      ui.toast('error', 'Force stop failed', errText(e));
    }
    return;
  }
  const v = await ui.ask({
    title: `Kill ${displayName(s)}'s session?`,
    body: 'tmux kill-session ends the process tree immediately. Nothing the app would save on exit is saved.',
    detail: app?.forceWarning ?? undefined,
    tone: 'danger',
    buttons: [
      { label: 'Cancel', value: 'cancel' },
      { label: 'Kill session', value: 'kill', kind: 'danger' },
    ],
    cancel: 'cancel',
  });
  if (v !== 'kill') return;
  try {
    await api.forceStop(name, true);
  } catch (e) {
    ui.toast('error', 'Kill failed', errText(e));
  }
}

export async function run(label: string, p: Promise<unknown>) {
  try {
    await p;
  } catch (e) {
    ui.toast('error', label, errText(e));
  }
}
