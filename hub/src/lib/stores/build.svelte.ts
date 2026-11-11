// colcon build state and the Build action (asks first when apps run).

import { api, errText } from '../ipc';
import type { BuildState } from '../types';
import { displayName, sessions } from './sessions.svelte';
import { ui } from './ui.svelte';

class Build {
  state = $state<BuildState | null>(null);
  packages = $state<string[]>([]);
  packagesError = $state<string | null>(null);

  get running(): boolean {
    return this.state?.running ?? false;
  }

  get done(): number {
    return (this.state?.packages ?? []).filter((p) => p.status !== 'building').length;
  }

  async refresh() {
    try {
      this.state = await api.buildState();
    } catch {
      /* event brings it */
    }
  }

  async loadPackages(force = false) {
    try {
      this.packages = await api.listPackages(force);
      this.packagesError = null;
    } catch (e) {
      this.packagesError = errText(e);
    }
  }

  async start(packages: string[] = []) {
    if (this.running) {
      ui.drawerOpen = true;
      ui.toast('info', 'A build is already running');
      return;
    }
    const live = sessions.live;
    if (live.length > 0) {
      const names = live.map(displayName);
      const list =
        names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
      const v = await ui.ask({
        title: 'Build while apps are running?',
        body: `${list} ${names.length === 1 ? 'is' : 'are'} running; ${
          names.length === 1 ? 'it keeps' : 'they keep'
        } the old install until restarted.`,
        tone: 'warning',
        buttons: [
          { label: 'Cancel', value: 'cancel' },
          { label: 'Build anyway', value: 'build', kind: 'primary' },
        ],
        cancel: 'cancel',
      });
      if (v !== 'build') return;
    }
    try {
      await api.build(packages);
      ui.drawerOpen = true;
    } catch (e) {
      ui.toast('error', 'Build did not start', errText(e));
    }
  }

  async cancel() {
    try {
      await api.cancelBuild();
    } catch (e) {
      ui.toast('error', 'Cancel failed', errText(e));
    }
  }
}

export const build = new Build();
