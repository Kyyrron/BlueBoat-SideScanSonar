// Typed wrappers over the hub's Tauri commands and events. This file is the
// whole surface between the webview and the Rust side.

import { Channel, invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import type {
  AppsView,
  BuildState,
  DataView,
  EnvView,
  LaunchOutcome,
  LogFile,
  ParamChoice,
  SessionView,
  TermMsg,
} from './types';

export const api = {
  listApps: () => invoke<AppsView>('list_apps'),
  paramChoices: (app: string, param: string) => invoke<ParamChoice[]>('param_choices', { app, param }),
  launch: (app: string, params: Record<string, string> = {}, variant: string | null = null) =>
    invoke<LaunchOutcome>('launch', { app, params, variant }),
  stop: (session: string) => invoke<void>('stop', { session }),
  cancelStop: (session: string) => invoke<void>('cancel_stop', { session }),
  forceStop: (session: string, kill: boolean) => invoke<void>('force_stop', { session, kill }),
  focus: (session: string) => invoke<void>('focus', { session }),
  restart: (session: string) => invoke<void>('restart', { session }),
  dismiss: (session: string) => invoke<void>('dismiss', { session }),
  sessions: () => invoke<SessionView[]>('sessions'),
  attach: (session: string, ch: Channel<TermMsg>) => invoke<void>('attach', { session, onEvent: ch }),
  detach: (session: string) => invoke<void>('detach', { session }),
  writeStdin: (session: string, data: string) => invoke<void>('write_stdin', { session, data }),
  resize: (session: string, cols: number, rows: number) => invoke<void>('resize', { session, cols, rows }),
  listPackages: (force = false) => invoke<string[]>('list_packages', { force }),
  build: (packages: string[]) => invoke<void>('build', { packages }),
  cancelBuild: () => invoke<void>('cancel_build'),
  buildState: () => invoke<BuildState>('build_state'),
  scanData: (force = false) => invoke<DataView>('scan_data', { force }),
  openPath: (path: string) => invoke<void>('open_path', { path }),
  openUrl: (url: string) => invoke<void>('open_url', { url }),
  openAppFolder: (app: string) => invoke<void>('open_app_folder', { app }),
  openInApp: (app: string, param: string, path: string) =>
    invoke<LaunchOutcome>('open_in_app', { app, param, path }),
  listLogs: () => invoke<LogFile[]>('list_logs'),
  envStatus: () => invoke<EnvView>('env_status'),
  quitHub: () => invoke<void>('quit_hub'),
};

export function on<T>(event: string, cb: (payload: T) => void): Promise<UnlistenFn> {
  return listen<T>(event, (e) => cb(e.payload));
}

export { Channel };

/** Error text from a rejected invoke. */
export function errText(e: unknown): string {
  if (typeof e === 'string') return e;
  if (e instanceof Error) return e.message;
  return String(e);
}
