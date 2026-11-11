<script lang="ts">
  import { Monitor, Moon, Sun } from '@lucide/svelte';
  import { env } from '../stores/data.svelte';
  import { apps } from '../stores/apps.svelte';
  import { ui, type Theme } from '../stores/ui.svelte';
  import { retheme, setTerminalFontSize } from '../terminal';

  const themes: { id: Theme; label: string; icon: typeof Sun }[] = [
    { id: 'system', label: 'System', icon: Monitor },
    { id: 'dark', label: 'Dark', icon: Moon },
    { id: 'light', label: 'Light', icon: Sun },
  ];

  function pickTheme(t: Theme) {
    ui.setTheme(t);
    requestAnimationFrame(retheme);
  }

  const e = $derived(env.view);
</script>

<div class="scroll">
  <h2>Settings</h2>

  <section class="card panel">
    <div class="section-title">Appearance</div>
    <div class="row">
      <span class="lbl">Theme</span>
      <div class="seg" role="radiogroup" aria-label="Theme">
        {#each themes as t (t.id)}
          <button role="radio" aria-checked={ui.theme === t.id} class:on={ui.theme === t.id} onclick={() => pickTheme(t.id)}>
            <t.icon size={14} />{t.label}
          </button>
        {/each}
      </div>
    </div>
    <div class="row">
      <label class="lbl" for="fs">Terminal font size</label>
      <input
        id="fs"
        type="range"
        min="10"
        max="18"
        step="1"
        value={ui.fontSize}
        oninput={(ev) => {
          const v = Number((ev.target as HTMLInputElement).value);
          ui.setFontSize(v);
          setTerminalFontSize(v);
        }}
      />
      <span class="mono">{ui.fontSize}px</span>
    </div>
  </section>

  <section class="card panel">
    <div class="section-title">Where things are</div>
    <dl class="selectable">
      <dt>App registry</dt>
      <dd class="mono">{apps.view?.configPath ?? '…'} <span class="faint">(hot-reloaded on save)</span></dd>
      <dt>Workspace</dt>
      <dd class="mono">{e?.workspace ?? '…'}</dd>
      <dt>Data root</dt>
      <dd class="mono">
        {e?.dataRoot ?? '…'}
        <span class="faint">({e?.probe.dataDirEnv ? '$BLUEBOAT_DATA_DIR from ~/.bashrc' : 'default: workspace/data'})</span>
      </dd>
      <dt>Hub state &amp; logs</dt>
      <dd class="mono">{e?.stateDir ?? '…'}</dd>
      <dt>tmux</dt>
      <dd class="mono">{e?.tmux ?? 'not found'} · socket <strong>{e?.socket ?? 'blueboat-hub'}</strong> <span class="faint">(tmux -L {e?.socket ?? 'blueboat-hub'} ls)</span></dd>
      <dt>Window control</dt>
      <dd>
        {#if e?.x11}
          <span class="ok">X11 ({e.sessionType || 'x11'})</span> — Stop closes windows like their ✕, Focus raises them.
        {:else}
          <span class="warn">No X11 display ({e?.sessionType || 'unknown'})</span> — Stop falls back to Ctrl-C and Focus is unavailable.
        {/if}
      </dd>
      <dt>Apps' shell</dt>
      <dd>
        {#if e?.probe.error}<span class="warn">{e.probe.error}</span>
        {:else if e?.probe.done}ROS {e.probe.rosDistro ?? 'not sourced'} as ~/.bashrc sets it
        {:else}checking…{/if}
      </dd>
    </dl>
  </section>

  <section class="card panel">
    <div class="section-title">Keyboard</div>
    <dl class="keys">
      <dt><kbd>Ctrl K</kbd></dt>
      <dd>Command palette</dd>
      <dt><kbd>Ctrl B</kbd></dt>
      <dd>Build all packages</dd>
      <dt><kbd>Ctrl 1…9</kbd></dt>
      <dd>Show the n-th running terminal</dd>
      <dt><kbd>Ctrl Shift F</kbd></dt>
      <dd>Search the current terminal</dd>
      <dt><kbd>Ctrl Shift C / V</kbd></dt>
      <dd>Copy selection / paste into a terminal</dd>
      <dt><kbd>Esc</kbd></dt>
      <dd>Leave the maximized or tiled view</dd>
    </dl>
  </section>
</div>

<style>
  .scroll {
    height: 100%;
    overflow: auto;
    padding: var(--s5);
    max-width: 980px;
  }
  h2 {
    margin: 0 0 var(--s5);
    font-size: 20px;
    font-weight: 600;
  }
  .panel {
    padding: var(--s4) var(--s5);
    margin-bottom: var(--s4);
  }
  .row {
    display: flex;
    align-items: center;
    gap: var(--s4);
    margin-top: var(--s4);
  }
  .lbl {
    width: 160px;
    color: var(--muted);
    font-size: 13px;
  }
  .seg {
    display: inline-flex;
    padding: 3px;
    border-radius: 9px;
    background: var(--sunken);
    border: 1px solid var(--border);
  }
  .seg button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 12px;
    border: 0;
    border-radius: 6px;
    background: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 13px;
  }
  .seg button.on {
    background: var(--raised);
    color: var(--text);
    box-shadow: 0 0 0 1px var(--border-strong);
  }
  input[type='range'] {
    width: 200px;
    accent-color: var(--accent);
  }
  dl {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 10px 16px;
    margin: var(--s4) 0 0;
    font-size: 13px;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  dd.mono {
    font-size: 12px;
  }
  .keys dt {
    color: var(--text);
  }
  .ok {
    color: var(--running);
  }
  .warn {
    color: var(--warning);
  }
</style>
