// The app registry as the hub sees it (apps.toml + availability + last run).

import { api, errText } from '../ipc';
import type { AppView, AppsView } from '../types';
import { ui } from './ui.svelte';

class Apps {
  view = $state<AppsView | null>(null);
  loading = $state(true);

  get list(): AppView[] {
    return this.view?.apps ?? [];
  }

  byId(id: string): AppView | undefined {
    return this.view?.apps.find((a) => a.id === id);
  }

  async refresh() {
    try {
      this.view = await api.listApps();
    } catch (e) {
      ui.toast('error', 'Could not read the app registry', errText(e));
    } finally {
      this.loading = false;
    }
  }
}

export const apps = new Apps();
