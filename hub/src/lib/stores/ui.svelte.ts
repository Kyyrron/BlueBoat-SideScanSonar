// View state, toasts, dialogs and per-viewer preferences.

export type View = 'apps' | 'data' | 'build' | 'logs' | 'settings';
export type Theme = 'system' | 'dark' | 'light';

export interface Toast {
  id: number;
  kind: 'info' | 'success' | 'warning' | 'error';
  text: string;
  detail?: string;
}

export interface ConfirmButton {
  label: string;
  value: string;
  kind?: 'default' | 'primary' | 'danger';
}

export interface ConfirmRequest {
  title: string;
  body: string;
  detail?: string;
  tone?: 'default' | 'danger' | 'warning';
  buttons: ConfirmButton[];
  /** value returned by Esc / backdrop */
  cancel: string;
  resolve: (v: string) => void;
}

export interface ParamRequest {
  app: string;
  variant: string | null;
  initial: Record<string, string>;
}

function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(`bbhub.${key}`);
    return v == null ? fallback : (JSON.parse(v) as T);
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try {
    localStorage.setItem(`bbhub.${key}`, JSON.stringify(value));
  } catch {
    /* private mode / blocked storage: preferences just don't persist */
  }
}

export const reducedMotion = (): boolean =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Run a layout change inside a view transition (FLIP-like morph), if available. */
export function morph(update: () => void | Promise<void>) {
  const doc = document as Document & {
    startViewTransition?: (cb: () => void | Promise<void>) => unknown;
  };
  if (!doc.startViewTransition || reducedMotion() || document.hidden) {
    void update();
    return;
  }
  doc.startViewTransition(update);
}

class UI {
  view = $state<View>('apps');
  maximized = $state<string | null>(null);
  tiled = $state(false);
  /** running cards shrunk back to tile size */
  collapsed = $state<Record<string, boolean>>({});
  drawerOpen = $state(false);
  drawerHeight = $state<number>(load('drawerHeight', 320));
  paletteOpen = $state(false);
  packagePickerOpen = $state(false);
  theme = $state<Theme>(load('theme', 'system'));
  fontSize = $state<number>(load('fontSize', 13));
  groupOpen = $state<Record<string, boolean>>(load('groupOpen', {}));
  toasts = $state<Toast[]>([]);
  confirm = $state<ConfirmRequest | null>(null);
  params = $state<ParamRequest | null>(null);
  /** terminal that last had focus (for Ctrl+Shift+F) */
  activeTerm = $state<string | null>(null);
  /** terminal whose search bar is open */
  searchOpen = $state<string | null>(null);
  /** sessions where the first force-stop stage (C-c) was sent */
  ctrlCSent = $state<Record<string, number>>({});
  quitWaiting = $state<string[] | null>(null);
  now = $state(Date.now());
  windowFocused = $state(true);

  #toastId = 0;

  constructor() {
    setInterval(() => (this.now = Date.now()), 1000);
  }

  setTheme(t: Theme) {
    this.theme = t;
    save('theme', t);
    applyTheme(t);
  }

  setFontSize(px: number) {
    this.fontSize = px;
    save('fontSize', px);
  }

  setDrawerHeight(px: number) {
    this.drawerHeight = px;
    save('drawerHeight', px);
  }

  toggleGroup(id: string, open: boolean) {
    this.groupOpen = { ...this.groupOpen, [id]: open };
    save('groupOpen', this.groupOpen);
  }

  toast(kind: Toast['kind'], text: string, detail?: string, ms?: number) {
    const id = ++this.#toastId;
    this.toasts = [...this.toasts, { id, kind, text, detail }];
    const life = ms ?? (kind === 'error' ? 9000 : kind === 'warning' ? 7000 : 4500);
    setTimeout(() => this.dismissToast(id), life);
  }

  dismissToast(id: number) {
    this.toasts = this.toasts.filter((t) => t.id !== id);
  }

  ask(req: Omit<ConfirmRequest, 'resolve'>): Promise<string> {
    return new Promise((resolve) => {
      this.confirm = {
        ...req,
        resolve: (v) => {
          this.confirm = null;
          resolve(v);
        },
      };
    });
  }

  maximize(session: string | null) {
    morph(() => {
      this.maximized = session;
      if (session) {
        this.tiled = false;
        this.collapsed = { ...this.collapsed, [session]: false };
        this.activeTerm = session;
      }
    });
  }

  setTiled(on: boolean) {
    morph(() => {
      this.tiled = on;
      if (on) this.maximized = null;
    });
  }

  setCollapsed(session: string, on: boolean) {
    morph(() => {
      this.collapsed = { ...this.collapsed, [session]: on };
      if (on && this.maximized === session) this.maximized = null;
    });
  }
}

export function applyTheme(t: Theme) {
  const root = document.documentElement;
  if (t === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', t);
}

export const ui = new UI();
