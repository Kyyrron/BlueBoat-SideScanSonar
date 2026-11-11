<script lang="ts">
  import { Play, Search } from '@lucide/svelte';
  import { untrack } from 'svelte';
  import { api, errText } from '../ipc';
  import { ago } from '../format';
  import { apps } from '../stores/apps.svelte';
  import { doLaunch } from '../stores/sessions.svelte';
  import { ui } from '../stores/ui.svelte';
  import type { ParamChoice, ParamSpec } from '../types';

  const req = $derived(ui.params);
  const app = $derived(req ? apps.byId(req.app) : undefined);

  let values = $state<Record<string, string>>({});
  let variant = $state<string>('');
  let choices = $state<Record<string, ParamChoice[] | null>>({});
  let filter = $state<Record<string, string>>({});
  let busy = $state(false);

  // Load once per dialog opening. The effect tracks only the request object:
  // everything else runs untracked, so filling `choices` (or an app-list
  // refresh replacing `app`) can't re-run it and restart the listing.
  let loadedFor: object | null = null;
  $effect(() => {
    const r = req;
    untrack(() => {
      if (!r) {
        loadedFor = null;
        return;
      }
      if (r === loadedFor) return;
      const a = apps.byId(r.app);
      if (!a) return;
      loadedFor = r;
      values = Object.fromEntries(a.params.map((p) => [p.name, r.initial[p.name] ?? p.default ?? '']));
      variant = r.variant ?? '';
      filter = {};
      const pending: Record<string, ParamChoice[] | null> = {};
      for (const p of a.params) {
        if (p.kind !== 'path' && p.kind !== 'file') continue;
        pending[p.name] = null;
        api
          .paramChoices(a.id, p.name)
          .then((c) => {
            if (loadedFor === r) choices = { ...choices, [p.name]: c };
          })
          .catch((e) => {
            if (loadedFor !== r) return;
            choices = { ...choices, [p.name]: [] };
            ui.toast('error', `Could not list ${p.label ?? p.name}`, errText(e));
          });
      }
      choices = pending;
    });
  });

  const missing = $derived(app ? app.params.filter((p) => !p.optional && !values[p.name]) : []);

  function close() {
    ui.params = null;
  }

  async function go() {
    if (!app || missing.length) return;
    busy = true;
    const params = Object.fromEntries(Object.entries(values).filter(([, v]) => v !== ''));
    const ok = await doLaunch(app.id, params, variant || null);
    busy = false;
    if (ok) close();
  }

  function shown(p: ParamSpec): ParamChoice[] {
    const list = choices[p.name] ?? [];
    const f = (filter[p.name] ?? '').toLowerCase();
    return f ? list.filter((c) => c.label.toLowerCase().includes(f)) : list;
  }

  function onKey(e: KeyboardEvent) {
    if (!req) return;
    if (e.key === 'Escape') {
      e.stopPropagation();
      close();
    }
  }
</script>

<svelte:window onkeydown={onKey} />

{#if req && app}
  <div class="backdrop" role="presentation" onpointerdown={(e) => e.target === e.currentTarget && close()}>
    <div class="dialog card" role="dialog" aria-modal="true" aria-labelledby="pd-title">
      <h2 id="pd-title">Launch {app.name}</h2>
      <p class="muted cmd mono">{app.command}</p>

      {#if app.variants.length}
        <div class="field">
          <label for="pd-variant">Variant</label>
          <select id="pd-variant" bind:value={variant}>
            <option value="">{app.name}</option>
            {#each app.variants as v (v.id)}<option value={v.id}>{v.name}</option>{/each}
          </select>
        </div>
      {/if}

      {#each app.params as p (p.name)}
        <div class="field">
          <label for={`pd-${p.name}`}>
            {p.label ?? p.name}
            {#if p.optional}<span class="faint">optional</span>{/if}
          </label>
          {#if p.kind === 'number'}
            <input
              id={`pd-${p.name}`}
              type="number"
              min={p.min ?? undefined}
              max={p.max ?? undefined}
              bind:value={values[p.name]}
              placeholder={p.optional ? 'default' : ''}
            />
          {:else if p.kind === 'choice'}
            <select id={`pd-${p.name}`} bind:value={values[p.name]}>
              {#if p.optional}<option value="">—</option>{/if}
              {#each p.choices as c (c)}<option value={c}>{c}</option>{/each}
            </select>
          {:else}
            <div class="picker">
              <div class="filter">
                <Search size={14} />
                <input id={`pd-${p.name}`} bind:value={filter[p.name]} placeholder={`Filter ${p.root ?? ''}`} />
              </div>
              <div class="opts" role="listbox" aria-label={p.label ?? p.name}>
                {#if p.optional}
                  <button role="option" aria-selected={!values[p.name]} class:on={!values[p.name]} onclick={() => (values[p.name] = '')}>
                    <span class="lbl muted">None — start without one</span>
                  </button>
                {/if}
                {#if choices[p.name] == null}
                  {#each [1, 2, 3] as k (k)}<div class="skeleton sk"></div>{/each}
                {:else}
                  {#each shown(p) as c (c.value)}
                    <button role="option" aria-selected={values[p.name] === c.value} class:on={values[p.name] === c.value} onclick={() => (values[p.name] = c.value)} ondblclick={go}>
                      <span class="lbl mono">{c.label}</span>
                      <span class="faint age">{ago(c.mtimeMs, ui.now)}</span>
                    </button>
                  {:else}
                    <div class="none muted">
                      {(choices[p.name] ?? []).length ? 'Nothing matches the filter.' : `Nothing under ${p.root}${p.marker ? ` with ${p.marker}` : ''}${p.glob ? ` matching ${p.glob}` : ''}.`}
                    </div>
                  {/each}
                {/if}
              </div>
            </div>
          {/if}
        </div>
      {/each}

      <div class="actions">
        <button class="btn" onclick={close}>Cancel</button>
        <button class="btn primary" onclick={go} disabled={busy || missing.length > 0} title={missing.length ? `Choose ${missing.map((m) => m.label ?? m.name).join(', ')}` : ''}>
          <Play size={14} />Launch
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: grid;
    place-items: center;
    background: var(--overlay);
  }
  .dialog {
    width: min(620px, calc(100vw - 32px));
    max-height: calc(100vh - 64px);
    overflow: auto;
    padding: var(--s5);
    box-shadow: var(--shadow);
  }
  h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 600;
  }
  .cmd {
    margin: 4px 0 var(--s4);
    font-size: 11.5px;
  }
  .field {
    margin-top: var(--s4);
  }
  label {
    display: flex;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 500;
  }
  input[type='number'],
  select {
    width: 100%;
    height: 34px;
    padding: 0 10px;
    border-radius: var(--r-ctl);
    border: 1px solid var(--border-strong);
    background: var(--sunken);
  }
  .picker {
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    overflow: hidden;
  }
  .filter {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 10px;
    height: 36px;
    border-bottom: 1px solid var(--border);
    color: var(--muted);
    background: var(--sunken);
  }
  .filter input {
    flex: 1;
    border: 0;
    outline: 0;
    background: transparent;
  }
  .opts {
    max-height: 280px;
    overflow: auto;
    padding: 4px;
  }
  .opts button {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 10px;
    border: 0;
    border-radius: 6px;
    background: none;
    text-align: left;
    cursor: pointer;
  }
  .opts button:hover {
    background: var(--raised);
  }
  .opts button.on {
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 50%, transparent);
  }
  .lbl {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12.5px;
  }
  .age {
    font-size: 12px;
    white-space: nowrap;
  }
  .sk {
    height: 28px;
    margin: 4px;
  }
  .none {
    padding: 12px;
    font-size: 13px;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--s2);
    margin-top: var(--s5);
  }
</style>
