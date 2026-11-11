// Mirrors of the Rust views (src-tauri/src/commands.rs, hub.rs, …).

export type ParamKind = 'path' | 'file' | 'number' | 'choice';

export interface ParamSpec {
  name: string;
  label?: string | null;
  kind: ParamKind;
  root?: string | null;
  glob?: string | null;
  marker?: string | null;
  depth?: number | null;
  optional: boolean;
  default?: string | null;
  choices: string[];
  format?: string | null;
  min?: number | null;
  max?: number | null;
}

export interface Variant {
  id: string;
  name: string;
  args: string;
}

export interface AppRun {
  startedMs: number;
  endedMs: number | null;
  exitCode: number | null;
  signal: number | null;
  params: Record<string, string>;
  variant: string | null;
}

export interface AppView {
  id: string;
  name: string;
  group: string;
  description: string;
  help: string | null;
  icon: string;
  singleton: boolean;
  window: boolean;
  stop: 'close' | 'ctrl-c';
  warning: string | null;
  forceWarning: string | null;
  primary: boolean;
  planned: boolean;
  optional: boolean;
  params: ParamSpec[];
  variants: Variant[];
  available: boolean;
  reason: string | null;
  fallback: boolean;
  command: string;
  cwd: string;
  lastRun: AppRun | null;
}

export interface Group {
  id: string;
  name: string;
  accent: string;
  collapsed: boolean;
}

export interface AppsView {
  groups: Group[];
  apps: AppView[];
  errors: string[];
  configPath: string;
  loadedMs: number;
}

export interface ParamChoice {
  value: string;
  label: string;
  mtimeMs: number;
}

export interface WinInfo {
  id: number;
  pid: number;
  transient: boolean;
  title: string;
}

export type SessionState = 'starting' | 'running' | 'stopping' | 'exited';

export interface SessionView {
  name: string;
  app: string;
  state: SessionState;
  pid: number;
  startedMs: number;
  exitCode: number | null;
  signal: number | null;
  windows: WinInfo[];
  stopRequestedMs: number | null;
  params: Record<string, string>;
  variant: string | null;
  log: string | null;
  stale: boolean;
  lastLine: string;
  restartPending: boolean;
}

export type LaunchOutcome =
  | { outcome: 'started'; session: string }
  | { outcome: 'alreadyRunning'; session: string; focused: boolean };

export type TermMsg =
  | { kind: 'history'; data: string }
  | { kind: 'output'; data: string }
  | { kind: 'ended' };

export type PkgStatus = 'building' | 'finished' | 'failed' | 'aborted';

export interface PkgProgress {
  name: string;
  status: PkgStatus;
  seconds: number | null;
}

export interface BuildState {
  running: boolean;
  session: string | null;
  startedMs: number;
  finishedMs: number | null;
  selection: string[];
  expected: number;
  packages: PkgProgress[];
  summary: string[];
  failed: string[];
  firstError: string | null;
  exitCode: number | null;
  ok: boolean | null;
}

export interface EntryAction {
  label: string;
  app: string;
  param: string;
  target: string;
}

export interface DataEntry {
  name: string;
  path: string;
  isDir: boolean;
  bytes: number;
  mtimeMs: number;
  action: EntryAction | null;
}

export interface DataTab {
  label: string;
  path: string;
  exists: boolean;
  count: number;
  totalBytes: number;
  newestName: string | null;
  newestMs: number | null;
  entries: DataEntry[];
}

export interface DataCard {
  id: string;
  name: string;
  icon: string;
  description: string;
  tabs: DataTab[];
}

export interface DataView {
  cards: DataCard[];
  scanning: boolean;
}

export interface LogFile {
  app: string;
  name: string;
  path: string;
  bytes: number;
  mtimeMs: number;
}

export interface Pill {
  ok: boolean;
  label: string;
  detail: string;
  ms: number | null;
}

export interface GitStatus {
  branch: string | null;
  modifiedSubmodules: string[];
  otherChanges: number;
}

export interface EnvProbe {
  done: boolean;
  rosDistro: string | null;
  dataDirEnv: string | null;
  error: string | null;
}

export interface EnvView {
  ros: Pill;
  venv: Pill;
  install: Pill;
  git: GitStatus;
  x11: boolean;
  sessionType: string;
  tmux: string | null;
  probe: EnvProbe;
  workspace: string;
  dataRoot: string;
  configPath: string;
  stateDir: string;
  logsDir: string;
  socket: string;
  nowMs: number;
}

export interface ExitEvent {
  session: string;
  app: string;
  appName: string;
  exitCode: number | null;
  signal: number | null;
  expected: boolean;
  removed: boolean;
}
