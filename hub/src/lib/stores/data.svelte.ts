// Data folder cards (read-only) and the environment pills.

import { api } from '../ipc';
import type { DataCard, EnvView } from '../types';

class Data {
  cards = $state<DataCard[] | null>(null);
  scanning = $state(false);
  scannedAt = $state<number | null>(null);

  set(cards: DataCard[]) {
    this.cards = cards;
    this.scanning = false;
    this.scannedAt = Date.now();
  }

  async refresh(force = false) {
    try {
      const v = await api.scanData(force);
      if (v.cards.length || this.cards == null) {
        this.cards = v.cards;
        if (v.cards.length) this.scannedAt = Date.now();
      }
      this.scanning = v.scanning;
    } catch {
      /* event brings it */
    }
  }
}

export const data = new Data();

class Env {
  view = $state<EnvView | null>(null);

  async refresh() {
    try {
      this.view = await api.envStatus();
    } catch {
      /* keep the last one */
    }
  }
}

export const env = new Env();
