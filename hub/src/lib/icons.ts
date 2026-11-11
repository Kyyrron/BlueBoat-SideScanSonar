// Icon names usable in apps.toml (`icon = "…"`) → lucide components.
// Unknown names fall back to `app-window`. Add an entry here to allow a new one.

import {
  Activity,
  AppWindow,
  AudioWaveform,
  Box,
  Brain,
  ChartLine,
  Cpu,
  Database,
  FileChartColumn,
  FileText,
  Folder,
  Gauge,
  Globe,
  Images,
  Layers,
  MapPin,
  Plane,
  Radar,
  Route,
  ScanEye,
  Ship,
  Terminal,
} from '@lucide/svelte';
import type { Component } from 'svelte';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IconComponent = Component<any>;

const ICONS: Record<string, IconComponent> = {
  activity: Activity,
  'app-window': AppWindow,
  'audio-waveform': AudioWaveform,
  box: Box,
  brain: Brain,
  'chart-line': ChartLine,
  cpu: Cpu,
  database: Database,
  'file-chart-column': FileChartColumn,
  'file-text': FileText,
  folder: Folder,
  gauge: Gauge,
  globe: Globe,
  images: Images,
  layers: Layers,
  'map-pin': MapPin,
  plane: Plane,
  radar: Radar,
  route: Route,
  'scan-eye': ScanEye,
  ship: Ship,
  terminal: Terminal,
};

export function iconFor(name: string | null | undefined): IconComponent {
  return (name && ICONS[name]) || AppWindow;
}
