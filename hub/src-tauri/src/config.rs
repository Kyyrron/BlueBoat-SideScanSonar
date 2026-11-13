//! `apps.toml`: the declarative app registry, its validation, command
//! rendering and the filesystem checks that decide whether a tile can launch.

use crate::paths::Resolver;
use crate::shell::{sh_quote, wildcard_match};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HubConfig {
    #[serde(default)]
    pub defaults: Defaults,
    #[serde(default)]
    pub build: BuildCfg,
    #[serde(default)]
    pub groups: Vec<Group>,
    #[serde(default)]
    pub apps: Vec<AppEntry>,
    #[serde(default)]
    pub data: Vec<DataCardCfg>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Defaults {
    /// The ROS workspace; `{workspace}` in the template.
    #[serde(default = "d_workspace")]
    pub workspace: String,
    /// argv prefix the script is handed to, e.g. `["bash", "-ic"]`.
    #[serde(default = "d_shell")]
    pub shell: Vec<String>,
    /// Script template: `{workspace}`, `{cwd}`, `{command}`.
    #[serde(default = "d_template")]
    pub template: String,
}

impl Default for Defaults {
    fn default() -> Self {
        Defaults {
            workspace: d_workspace(),
            shell: d_shell(),
            template: d_template(),
        }
    }
}

fn d_workspace() -> String {
    "~/ros2_ws".into()
}
fn d_shell() -> Vec<String> {
    vec!["bash".into(), "-ic".into()]
}
fn d_template() -> String {
    "cd {workspace} && source env.sh && cd {cwd} && exec {command}".into()
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BuildCfg {
    /// Run from `{workspace}`; never sources `install/setup.bash` first.
    #[serde(default = "d_build_cmd")]
    pub command: String,
    #[serde(default = "d_select_flag")]
    pub select_flag: String,
    /// Packages listed first in the package picker.
    #[serde(default)]
    pub pinned_first: Vec<String>,
}

impl Default for BuildCfg {
    fn default() -> Self {
        BuildCfg {
            command: d_build_cmd(),
            select_flag: d_select_flag(),
            pinned_first: vec![],
        }
    }
}

fn d_build_cmd() -> String {
    "source /opt/ros/jazzy/setup.bash && colcon build".into()
}
fn d_select_flag() -> String {
    "--packages-select".into()
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Group {
    pub id: String,
    pub name: String,
    #[serde(default = "d_accent")]
    pub accent: String,
    #[serde(default)]
    pub collapsed: bool,
}

fn d_accent() -> String {
    "slate".into()
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AppEntry {
    pub id: String,
    pub name: String,
    pub group: String,
    #[serde(default)]
    pub description: String,
    /// Longer explanation behind the tile's ⓘ button (plain text, newlines kept).
    #[serde(default)]
    pub help: Option<String>,
    #[serde(default = "d_icon")]
    pub icon: String,
    /// Relative to the workspace (the template does the `cd`).
    #[serde(default = "d_cwd")]
    pub cwd: String,
    #[serde(default)]
    pub command: String,
    #[serde(default)]
    pub requires: Vec<Requirement>,
    /// Used when a `requires` check of `command` fails and these pass.
    #[serde(default)]
    pub fallback_command: Option<String>,
    #[serde(default)]
    pub fallback_requires: Vec<Requirement>,
    #[serde(default)]
    pub params: Vec<ParamSpec>,
    #[serde(default)]
    pub variants: Vec<Variant>,
    #[serde(default = "yes")]
    pub singleton: bool,
    /// The app opens a window; Stop closes it. `false` → Stop sends C-c.
    #[serde(default = "yes")]
    pub window: bool,
    #[serde(default)]
    pub warning: Option<String>,
    /// Extra text in the Force-stop confirmation.
    #[serde(default)]
    pub force_warning: Option<String>,
    #[serde(default)]
    pub primary: bool,
    #[serde(default)]
    pub planned: bool,
    #[serde(default)]
    pub optional: bool,
    /// colcon packages whose rebuild makes a running instance stale.
    #[serde(default)]
    pub packages: Vec<String>,
    /// What Stop does once the windows are gone but the process lives on.
    #[serde(default)]
    pub after_close: Option<AfterClose>,
    /// How Stop asks the app to end: close its windows (default) or Ctrl-C.
    #[serde(default)]
    pub stop: StopMode,
}

#[derive(Debug, Clone, Copy, Default, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum StopMode {
    /// `_NET_CLOSE_WINDOW`, like the window's ✕ — the app runs its own close handling.
    #[default]
    Close,
    /// Ctrl-C into the pane — for `ros2 launch` viewers whose window asks
    /// "really exit?" with nothing to save (Gazebo).
    CtrlC,
}

fn d_icon() -> String {
    "app-window".into()
}
fn d_cwd() -> String {
    ".".into()
}
fn yes() -> bool {
    true
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum AfterClose {
    /// Send C-c to the pane (the polite stop of `ros2 launch`).
    CtrlC,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Requirement {
    /// `pkg/executable` in `install/<pkg>/lib/<pkg>/`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ros_exe: Option<String>,
    /// `pkg/file.py` in `install/<pkg>/share/<pkg>/launch/`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub launch: Option<String>,
    /// A file (placeholders allowed; relative = from the workspace).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub file: Option<String>,
    /// A program in `<workspace>/.venv/bin`, `~/.local/bin` or `$PATH`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bin: Option<String>,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ParamKind {
    Path,
    File,
    Number,
    Choice,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ParamSpec {
    pub name: String,
    #[serde(default)]
    pub label: Option<String>,
    pub kind: ParamKind,
    /// Base directory for `path` / `file` (placeholders allowed).
    #[serde(default)]
    pub root: Option<String>,
    /// Filename pattern for `file` entries.
    #[serde(default)]
    pub glob: Option<String>,
    /// A `path` entry must contain this file.
    #[serde(default)]
    pub marker: Option<String>,
    /// `path`: the directory level below root (1 = children). `file`: max depth.
    #[serde(default)]
    pub depth: Option<u32>,
    #[serde(default)]
    pub optional: bool,
    #[serde(default)]
    pub default: Option<String>,
    #[serde(default)]
    pub choices: Vec<String>,
    /// How a present value is written into the command; `{}` = quoted value.
    #[serde(default)]
    pub format: Option<String>,
    #[serde(default)]
    pub min: Option<f64>,
    #[serde(default)]
    pub max: Option<f64>,
}

impl ParamSpec {
    pub fn label(&self) -> &str {
        self.label.as_deref().unwrap_or(&self.name)
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Variant {
    pub id: String,
    pub name: String,
    /// Appended to the command, verbatim.
    pub args: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DataCardCfg {
    pub id: String,
    pub name: String,
    #[serde(default = "d_folder_icon")]
    pub icon: String,
    #[serde(default)]
    pub description: String,
    pub tabs: Vec<DataTabCfg>,
    /// Entries are the directories this many levels below the tab path.
    #[serde(default = "d_depth")]
    pub depth: u32,
    /// Top-level names left out of the listing.
    #[serde(default)]
    pub exclude: Vec<String>,
    #[serde(default)]
    pub actions: Vec<EntryAction>,
}

fn d_folder_icon() -> String {
    "folder".into()
}
fn d_depth() -> u32 {
    1
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DataTabCfg {
    pub label: String,
    pub path: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EntryAction {
    pub label: String,
    pub app: String,
    pub param: String,
    /// `file` or `dir`.
    #[serde(default)]
    pub when: Option<String>,
    /// The entry's own name must match.
    #[serde(default)]
    pub glob: Option<String>,
    /// A dir entry containing a file matching this pattern; the file is passed.
    #[serde(default)]
    pub contains: Option<String>,
    /// A dir entry containing this file; the dir is passed.
    #[serde(default)]
    pub marker: Option<String>,
}

pub fn parse(text: &str) -> Result<HubConfig, String> {
    toml::from_str::<HubConfig>(text).map_err(|e| e.to_string())
}

fn valid_id(s: &str) -> bool {
    !s.is_empty()
        && s
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_')
}

/// `{name}` / `{name?}` placeholders of a command, in order.
pub fn placeholders(cmd: &str) -> Result<Vec<(String, bool)>, String> {
    let mut out = vec![];
    let mut rest = cmd;
    while let Some(start) = rest.find('{') {
        let after = &rest[start + 1..];
        let end = after
            .find('}')
            .ok_or_else(|| format!("unclosed `{{` in `{cmd}`"))?;
        let inner = &after[..end];
        let (name, optional) = match inner.strip_suffix('?') {
            Some(n) => (n, true),
            None => (inner, false),
        };
        if !valid_id(name) {
            return Err(format!("bad placeholder `{{{inner}}}` in `{cmd}`"));
        }
        out.push((name.to_string(), optional));
        rest = &after[end + 1..];
    }
    Ok(out)
}

pub fn validate(cfg: &HubConfig) -> Vec<String> {
    let mut errs = vec![];
    let groups: HashSet<&str> = cfg.groups.iter().map(|g| g.id.as_str()).collect();
    let mut ids = HashSet::new();
    if cfg.defaults.shell.is_empty() {
        errs.push("[defaults] shell is empty".into());
    }
    for key in ["{cwd}", "{command}"] {
        if !cfg.defaults.template.contains(key) {
            errs.push(format!("[defaults] template must contain {key}"));
        }
    }
    for a in &cfg.apps {
        let who = format!("app `{}`", a.id);
        if !valid_id(&a.id) {
            errs.push(format!("{who}: ids use lowercase letters, digits and `_` only"));
        }
        if a.id == "build" {
            errs.push(format!("{who}: the id `build` is reserved for the Build session"));
        }
        if !ids.insert(a.id.as_str()) {
            errs.push(format!("{who}: the id appears twice"));
        }
        if !groups.is_empty() && !groups.contains(a.group.as_str()) {
            errs.push(format!("{who}: unknown group `{}`", a.group));
        }
        if a.planned {
            continue;
        }
        if a.command.trim().is_empty() {
            errs.push(format!("{who}: `command` is empty"));
        }
        let mut names = HashSet::new();
        for p in &a.params {
            if !valid_id(&p.name) || !names.insert(p.name.as_str()) {
                errs.push(format!("{who}: bad or repeated parameter name `{}`", p.name));
            }
            match p.kind {
                ParamKind::Path | ParamKind::File if p.root.is_none() => {
                    errs.push(format!("{who}: parameter `{}` needs a `root`", p.name))
                }
                ParamKind::Choice if p.choices.is_empty() => {
                    errs.push(format!("{who}: parameter `{}` needs `choices`", p.name))
                }
                _ => {}
            }
            if let Some(f) = &p.format {
                if !f.contains("{}") {
                    errs.push(format!("{who}: parameter `{}`: `format` must contain {{}}", p.name));
                }
            }
        }
        for cmd in std::iter::once(&a.command).chain(a.fallback_command.iter()) {
            match placeholders(cmd) {
                Err(e) => errs.push(format!("{who}: {e}")),
                Ok(list) => {
                    for (n, optional) in list {
                        match a.params.iter().find(|p| p.name == n) {
                            None => errs.push(format!("{who}: `{{{n}}}` has no matching parameter")),
                            Some(p) if p.optional != optional => errs.push(format!(
                                "{who}: write `{{{n}?}}` for an optional parameter and `{{{n}}}` for a required one"
                            )),
                            _ => {}
                        }
                    }
                }
            }
        }
        let mut vids = HashSet::new();
        for v in &a.variants {
            if !vids.insert(v.id.as_str()) {
                errs.push(format!("{who}: variant `{}` appears twice", v.id));
            }
        }
        for r in a.requires.iter().chain(a.fallback_requires.iter()) {
            let n = [&r.ros_exe, &r.launch, &r.file, &r.bin]
                .iter()
                .filter(|o| o.is_some())
                .count();
            if n != 1 {
                errs.push(format!(
                    "{who}: each `requires` entry sets exactly one of ros_exe, launch, file, bin"
                ));
            }
        }
    }
    let mut dids = HashSet::new();
    for d in &cfg.data {
        if !dids.insert(d.id.as_str()) {
            errs.push(format!("data card `{}` appears twice", d.id));
        }
        if d.tabs.is_empty() {
            errs.push(format!("data card `{}` has no tabs", d.id));
        }
        for act in &d.actions {
            match cfg.apps.iter().find(|a| a.id == act.app) {
                None => errs.push(format!("data card `{}`: unknown app `{}`", d.id, act.app)),
                Some(a) if !a.params.iter().any(|p| p.name == act.param) => errs.push(format!(
                    "data card `{}`: app `{}` has no parameter `{}`",
                    d.id, act.app, act.param
                )),
                _ => {}
            }
        }
    }
    errs
}

/// Fill `{key}` placeholders in one pass, so a value can never introduce a
/// placeholder of its own.
pub fn fill(template: &str, values: &[(&str, &str)]) -> String {
    let mut out = String::with_capacity(template.len() + 64);
    let mut rest = template;
    while let Some(start) = rest.find('{') {
        out.push_str(&rest[..start]);
        let after = &rest[start..];
        match values
            .iter()
            .find(|(k, _)| after.starts_with(&format!("{{{k}}}")))
        {
            Some((k, v)) => {
                out.push_str(v);
                rest = &after[k.len() + 2..];
            }
            None => {
                out.push('{');
                rest = &after[1..];
            }
        }
    }
    out.push_str(rest);
    out
}

/// Substitute validated parameter values into a command. Present values go
/// through the parameter's `format` with the value shell-quoted; absent
/// optional ones vanish.
pub fn render_command(cmd: &str, params: &[ParamSpec], values: &HashMap<String, String>) -> String {
    let mut out = String::new();
    let mut rest = cmd;
    while let Some(start) = rest.find('{') {
        out.push_str(&rest[..start]);
        let after = &rest[start + 1..];
        let Some(end) = after.find('}') else {
            out.push_str(&rest[start..]);
            return out;
        };
        let inner = &after[..end];
        let name = inner.strip_suffix('?').unwrap_or(inner);
        match params.iter().find(|p| p.name == name) {
            Some(p) => {
                if let Some(v) = values.get(name).filter(|v| !v.is_empty()) {
                    let fmt = p.format.as_deref().unwrap_or("{}");
                    out.push_str(&fmt.replace("{}", &sh_quote(v)));
                } else if out.ends_with(' ') {
                    // drop the separator the vanished optional value leaves
                    out.pop();
                }
            }
            None => {
                out.push('{');
                out.push_str(inner);
                out.push('}');
            }
        }
        rest = &after[end + 1..];
    }
    out.push_str(rest);
    out.trim_end().to_string()
}

/// The full script handed to `shell` (e.g. `bash -ic <script>`).
pub fn render_script(defaults: &Defaults, cwd: &str, command: &str) -> String {
    let mut s = fill(
        &defaults.template,
        &[
            ("workspace", defaults.workspace.as_str()),
            ("cwd", &sh_quote(cwd)),
            ("command", command),
        ],
    );
    // tmux treats an argument ending in ';' as a command separator.
    if s.ends_with(';') {
        s.push(' ');
    }
    s
}

/// The build script: `cd {workspace} && <build.command> [--packages-select a b]`.
pub fn render_build_script(defaults: &Defaults, build: &BuildCfg, packages: &[String]) -> String {
    let mut s = format!("cd {} && {}", defaults.workspace, build.command);
    if !packages.is_empty() {
        s.push(' ');
        s.push_str(&build.select_flag);
        for p in packages {
            s.push(' ');
            s.push_str(&sh_quote(p));
        }
    }
    s
}

/// Check one requirement against the filesystem.
pub fn check_requirement(r: &Requirement, res: &Resolver) -> Result<(), String> {
    if let Some(spec) = &r.ros_exe {
        let (pkg, exe) = spec
            .split_once('/')
            .ok_or_else(|| format!("ros_exe `{spec}` must be `pkg/executable`"))?;
        let p = res.ws.join("install").join(pkg).join("lib").join(pkg).join(exe);
        if p.is_file() {
            return Ok(());
        }
        return Err(if res.ws.join("install").join(pkg).is_dir() {
            format!("`{exe}` is missing from the {pkg} install — run Build")
        } else {
            format!("{pkg} isn't built yet — run Build")
        });
    }
    if let Some(spec) = &r.launch {
        let (pkg, file) = spec
            .split_once('/')
            .ok_or_else(|| format!("launch `{spec}` must be `pkg/file.py`"))?;
        let p = res
            .ws
            .join("install")
            .join(pkg)
            .join("share")
            .join(pkg)
            .join("launch")
            .join(file);
        if p.is_file() {
            return Ok(());
        }
        return Err(if res.ws.join("install").join(pkg).is_dir() {
            format!("{file} is missing from the {pkg} install — run Build")
        } else {
            format!("{pkg} isn't built yet — run Build")
        });
    }
    if let Some(f) = &r.file {
        let p = res.expand(f);
        return if p.exists() {
            Ok(())
        } else {
            Err(format!("{} not found", p.display()))
        };
    }
    if let Some(b) = &r.bin {
        return if find_bin(b, res).is_some() {
            Ok(())
        } else {
            Err(format!("`{b}` is not installed (not in .venv/bin or on PATH)"))
        };
    }
    Ok(())
}

pub fn find_bin(name: &str, res: &Resolver) -> Option<PathBuf> {
    let mut dirs = vec![res.ws.join(".venv/bin"), res.home.join(".local/bin")];
    if let Some(path) = std::env::var_os("PATH") {
        dirs.extend(std::env::split_paths(&path));
    }
    dirs.into_iter().map(|d| d.join(name)).find(|p| p.is_file())
}

/// Which command a launch uses, or why the tile is unavailable.
#[derive(Debug, Clone, PartialEq)]
pub struct Choice {
    pub command: String,
    pub fallback: bool,
}

pub fn choose_command(app: &AppEntry, res: &Resolver) -> Result<Choice, String> {
    if app.planned {
        return Err(format!("{} is planned, not built yet", app.name));
    }
    let primary = app
        .requires
        .iter()
        .try_for_each(|r| check_requirement(r, res));
    match primary {
        Ok(()) => Ok(Choice {
            command: app.command.clone(),
            fallback: false,
        }),
        Err(reason) => match &app.fallback_command {
            Some(fb) => app
                .fallback_requires
                .iter()
                .try_for_each(|r| check_requirement(r, res))
                .map(|_| Choice {
                    command: fb.clone(),
                    fallback: true,
                })
                .map_err(|_| reason),
            None => Err(reason),
        },
    }
}

/// Validate one parameter value. Returns the normalized value, or `None`
/// for an absent optional one.
pub fn validate_param(
    p: &ParamSpec,
    raw: Option<&str>,
    res: &Resolver,
) -> Result<Option<String>, String> {
    let raw = raw.map(str::trim).filter(|s| !s.is_empty());
    let raw = match raw {
        Some(v) => v.to_string(),
        None => match &p.default {
            Some(d) if !d.is_empty() => d.clone(),
            _ if p.optional => return Ok(None),
            _ => return Err(format!("{} is required", p.label())),
        },
    };
    match p.kind {
        ParamKind::Number => {
            let v: f64 = raw
                .parse()
                .map_err(|_| format!("{} must be a number", p.label()))?;
            if !v.is_finite() {
                return Err(format!("{} must be a number", p.label()));
            }
            if p.min.is_some_and(|m| v < m) || p.max.is_some_and(|m| v > m) {
                return Err(format!(
                    "{} must be between {} and {}",
                    p.label(),
                    p.min.map(|m| m.to_string()).unwrap_or("-∞".into()),
                    p.max.map(|m| m.to_string()).unwrap_or("∞".into())
                ));
            }
            Ok(Some(if v.fract() == 0.0 && v.abs() < 1e15 {
                format!("{}", v as i64)
            } else {
                v.to_string()
            }))
        }
        ParamKind::Choice => {
            if p.choices.iter().any(|c| c == &raw) {
                Ok(Some(raw))
            } else {
                Err(format!("{}: `{raw}` is not one of the choices", p.label()))
            }
        }
        ParamKind::Path | ParamKind::File => {
            let root = res.expand(p.root.as_deref().unwrap_or("."));
            let root = root
                .canonicalize()
                .map_err(|_| format!("{} does not exist", root.display()))?;
            let value = res.expand(&raw);
            let value = value
                .canonicalize()
                .map_err(|_| format!("{} does not exist", value.display()))?;
            if !value.starts_with(&root) {
                return Err(format!("{} must be inside {}", p.label(), root.display()));
            }
            if p.kind == ParamKind::Path {
                if !value.is_dir() {
                    return Err(format!("{} must be a folder", p.label()));
                }
                if let Some(m) = &p.marker {
                    if !value.join(m).is_file() {
                        return Err(format!("{} has no {m}", value.display()));
                    }
                }
            } else {
                if !value.is_file() {
                    return Err(format!("{} must be a file", p.label()));
                }
                if let Some(g) = &p.glob {
                    let name = value.file_name().and_then(|n| n.to_str()).unwrap_or("");
                    if !wildcard_match(g, name) {
                        return Err(format!("{} must match {g}", p.label()));
                    }
                }
            }
            Ok(Some(value.to_string_lossy().into_owned()))
        }
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ParamChoice {
    pub value: String,
    pub label: String,
    pub mtime_ms: i64,
}

/// Candidates for a `path` / `file` parameter, newest first.
pub fn param_choices(p: &ParamSpec, res: &Resolver) -> Vec<ParamChoice> {
    let Some(root) = p.root.as_deref().map(|r| res.expand(r)) else {
        return vec![];
    };
    let mut out = vec![];
    match p.kind {
        ParamKind::Path => {
            let level = p.depth.unwrap_or(1).max(1);
            collect_dirs(&root, &root, level, p.marker.as_deref(), &mut out);
        }
        ParamKind::File => {
            let depth = p.depth.unwrap_or(1).max(1);
            collect_files(&root, &root, depth, p.glob.as_deref(), &mut out);
        }
        _ => {}
    }
    out.sort_by_key(|c| std::cmp::Reverse(c.mtime_ms));
    out.truncate(1000);
    out
}

pub fn mtime_ms(p: &Path) -> i64 {
    std::fs::symlink_metadata(p)
        .and_then(|m| m.modified())
        .ok()
        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

fn sorted_children(dir: &Path) -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .map(|rd| {
            rd.filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| {
                    !p.file_name()
                        .and_then(|n| n.to_str())
                        .is_some_and(|n| n.starts_with('.'))
                })
                .collect()
        })
        .unwrap_or_default();
    v.sort();
    v
}

fn rel_label(root: &Path, p: &Path) -> String {
    p.strip_prefix(root)
        .map(|r| r.to_string_lossy().into_owned())
        .unwrap_or_else(|_| p.to_string_lossy().into_owned())
}

fn collect_dirs(root: &Path, dir: &Path, level: u32, marker: Option<&str>, out: &mut Vec<ParamChoice>) {
    for c in sorted_children(dir) {
        if !c.is_dir() {
            continue;
        }
        if level > 1 {
            collect_dirs(root, &c, level - 1, marker, out);
        } else if marker.is_none_or(|m| c.join(m).is_file()) {
            out.push(ParamChoice {
                value: c.to_string_lossy().into_owned(),
                label: rel_label(root, &c),
                mtime_ms: mtime_ms(&c),
            });
        }
    }
}

fn collect_files(root: &Path, dir: &Path, depth: u32, glob: Option<&str>, out: &mut Vec<ParamChoice>) {
    for c in sorted_children(dir) {
        if c.is_dir() {
            if depth > 1 {
                collect_files(root, &c, depth - 1, glob, out);
            }
        } else if glob.is_none_or(|g| {
            c.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| wildcard_match(g, n))
        }) {
            out.push(ParamChoice {
                value: c.to_string_lossy().into_owned(),
                label: rel_label(root, &c),
                mtime_ms: mtime_ms(&c),
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn res_at(ws: &Path) -> Resolver {
        Resolver {
            home: ws.to_path_buf(),
            ws: ws.to_path_buf(),
            data_root: ws.join("data"),
            superproject: ws.join("src/SP"),
        }
    }

    /// The shipped registry must parse and validate.
    #[test]
    fn shipped_apps_toml_is_valid() {
        let text = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/../apps.toml"))
            .expect("apps.toml");
        let cfg = parse(&text).expect("parse");
        let errs = validate(&cfg);
        assert!(errs.is_empty(), "{errs:#?}");
        let ids: Vec<&str> = cfg.apps.iter().map(|a| a.id.as_str()).collect();
        for want in ["mcs", "gcs", "qgc", "world_builder", "gazebo_world", "sonar_simple", "log_reviewer", "aug_studio", "belief", "replanner"] {
            assert!(ids.contains(&want), "missing {want}");
        }
        // Belief and the Replanner were ghosts until their packages were built; now real tiles
        for id in ["belief", "replanner"] {
            let a = cfg.apps.iter().find(|a| a.id == id).unwrap();
            assert!(!a.planned && !a.command.is_empty(), "{id}");
        }
        // the two launches the hub must never start itself
        for a in &cfg.apps {
            assert!(!a.command.contains("BlueBoat_launch.py"), "{}", a.id);
            assert!(!a.command.contains("full_mission_launch.py"), "{}", a.id);
        }
    }

    #[test]
    fn rejects_unknown_fields_and_bad_entries() {
        assert!(parse("[[apps]]\nid='x'\nname='X'\ngroup='g'\ncomand='typo'\n").is_err());
        let cfg = parse(
            r#"
            [[groups]]
            id = "g"
            name = "G"
            [[apps]]
            id = "Bad-Id"
            name = "x"
            group = "nope"
            command = "run {missing}"
            [[apps]]
            id = "build"
            name = "b"
            group = "g"
            command = "x"
            "#,
        )
        .unwrap();
        let errs = validate(&cfg).join("\n");
        assert!(errs.contains("lowercase"), "{errs}");
        assert!(errs.contains("unknown group"), "{errs}");
        assert!(errs.contains("no matching parameter"), "{errs}");
        assert!(errs.contains("reserved"), "{errs}");
    }

    #[test]
    fn optional_marker_must_match() {
        let cfg = parse(
            r#"
            [[apps]]
            id = "a"
            name = "A"
            group = "g"
            command = "run {p}"
            params = [{ name = "p", kind = "number", optional = true }]
            "#,
        )
        .unwrap();
        assert!(validate(&cfg).join("\n").contains("optional"));
    }

    #[test]
    fn placeholder_scan() {
        assert_eq!(
            placeholders("a {x} b {y?}").unwrap(),
            vec![("x".to_string(), false), ("y".to_string(), true)]
        );
        assert!(placeholders("a {x").is_err());
        assert!(placeholders("a {X}").is_err());
    }

    #[test]
    fn command_rendering_quotes_values() {
        let params = vec![
            ParamSpec {
                name: "world".into(),
                label: None,
                kind: ParamKind::Path,
                root: Some("~/worlds".into()),
                glob: None,
                marker: None,
                depth: None,
                optional: false,
                default: None,
                choices: vec![],
                format: None,
                min: None,
                max: None,
            },
            ParamSpec {
                name: "range".into(),
                label: None,
                kind: ParamKind::Number,
                root: None,
                glob: None,
                marker: None,
                depth: None,
                optional: true,
                default: None,
                choices: vec![],
                format: Some("range_length_mm:={}".into()),
                min: None,
                max: None,
            },
        ];
        let mut v = HashMap::new();
        v.insert("world".to_string(), "/home/u/worlds/p/w 1".to_string());
        assert_eq!(
            render_command("ros2 launch x y.py world_dir:={world} {range?}", &params, &v),
            "ros2 launch x y.py world_dir:='/home/u/worlds/p/w 1'"
        );
        v.insert("range".to_string(), "20000".to_string());
        assert_eq!(
            render_command("ros2 launch x y.py world_dir:={world} {range?}", &params, &v),
            "ros2 launch x y.py world_dir:='/home/u/worlds/p/w 1' range_length_mm:=20000"
        );
        // a value can't smuggle a command
        v.insert("world".to_string(), "x'; rm -rf ~; '".to_string());
        let out = render_command("run {world}", &params[..1], &v);
        assert_eq!(out, "run 'x'\\''; rm -rf ~; '\\'''");
    }

    #[test]
    fn script_template() {
        let d = Defaults::default();
        assert_eq!(
            render_script(&d, "src/BlueBoat-SideScanSonar/BlueBoat-MCS", "python3 run.py"),
            "cd ~/ros2_ws && source env.sh && cd src/BlueBoat-SideScanSonar/BlueBoat-MCS && exec python3 run.py"
        );
        // `{cwd}` inside the command is not re-expanded
        assert_eq!(
            render_script(&d, ".", "echo {cwd}"),
            "cd ~/ros2_ws && source env.sh && cd . && exec echo {cwd}"
        );
        assert!(render_script(&d, ".", "echo x;").ends_with("; "));
    }

    #[test]
    fn build_script() {
        let d = Defaults::default();
        let b = BuildCfg::default();
        assert_eq!(
            render_build_script(&d, &b, &[]),
            "cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build"
        );
        assert_eq!(
            render_build_script(&d, &b, &["blueboat_interfaces".into(), "blueboat_sss".into()]),
            "cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build --packages-select blueboat_interfaces blueboat_sss"
        );
    }

    fn tempdir(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("bbhub-test-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn requirements_and_fallback() {
        let ws = tempdir("req");
        std::fs::create_dir_all(ws.join("install/pkg/lib/pkg")).unwrap();
        std::fs::write(ws.join("install/pkg/lib/pkg/tool"), "").unwrap();
        std::fs::create_dir_all(ws.join("install/pkg/share/pkg/launch")).unwrap();
        std::fs::write(ws.join("install/pkg/share/pkg/launch/a_launch.py"), "").unwrap();
        let res = res_at(&ws);
        let ok = |r: Requirement| check_requirement(&r, &res);
        assert!(ok(Requirement { ros_exe: Some("pkg/tool".into()), ..Default::default() }).is_ok());
        let e = ok(Requirement { ros_exe: Some("other/tool".into()), ..Default::default() }).unwrap_err();
        assert_eq!(e, "other isn't built yet — run Build");
        assert!(ok(Requirement { launch: Some("pkg/a_launch.py".into()), ..Default::default() }).is_ok());
        assert!(ok(Requirement { launch: Some("pkg/b_launch.py".into()), ..Default::default() })
            .unwrap_err()
            .contains("missing from the pkg install"));
        assert!(ok(Requirement { bin: Some("definitely-not-a-binary-xyz".into()), ..Default::default() }).is_err());

        let mut app = parse(
            r#"
            [[apps]]
            id = "a"
            name = "A"
            group = "g"
            command = "definitely-not-a-binary-xyz"
            requires = [{ bin = "definitely-not-a-binary-xyz" }]
            fallback_command = "python3 -m a"
            fallback_requires = [{ file = "install/pkg/lib/pkg/tool" }]
            "#,
        )
        .unwrap()
        .apps
        .remove(0);
        assert_eq!(
            choose_command(&app, &res).unwrap(),
            Choice { command: "python3 -m a".into(), fallback: true }
        );
        app.fallback_requires[0].file = Some("nope".into());
        assert!(choose_command(&app, &res).unwrap_err().contains("not installed"));
        let _ = std::fs::remove_dir_all(&ws);
    }

    #[test]
    fn path_params_are_confined_to_root() {
        let ws = tempdir("param");
        std::fs::create_dir_all(ws.join("worlds/p/w1")).unwrap();
        std::fs::write(ws.join("worlds/p/w1/world.sdf"), "").unwrap();
        std::fs::create_dir_all(ws.join("worlds/p/w2")).unwrap();
        std::fs::create_dir_all(ws.join("elsewhere")).unwrap();
        let res = res_at(&ws);
        let p = ParamSpec {
            name: "world".into(),
            label: Some("World".into()),
            kind: ParamKind::Path,
            root: Some("{workspace}/worlds".into()),
            glob: None,
            marker: Some("world.sdf".into()),
            depth: Some(2),
            optional: false,
            default: None,
            choices: vec![],
            format: None,
            min: None,
            max: None,
        };
        let good = ws.join("worlds/p/w1").to_string_lossy().into_owned();
        assert!(validate_param(&p, Some(&good), &res).unwrap().is_some());
        let no_marker = ws.join("worlds/p/w2").to_string_lossy().into_owned();
        assert!(validate_param(&p, Some(&no_marker), &res).unwrap_err().contains("world.sdf"));
        let escape = ws.join("worlds/../elsewhere").to_string_lossy().into_owned();
        assert!(validate_param(&p, Some(&escape), &res).unwrap_err().contains("inside"));
        assert!(validate_param(&p, None, &res).unwrap_err().contains("required"));
        let choices = param_choices(&p, &res);
        assert_eq!(choices.len(), 1);
        assert_eq!(choices[0].label, "p/w1");

        let n = ParamSpec { kind: ParamKind::Number, optional: true, min: Some(1.0), root: None, marker: None, ..p.clone() };
        assert_eq!(validate_param(&n, Some("20000"), &res).unwrap().as_deref(), Some("20000"));
        assert_eq!(validate_param(&n, Some(""), &res).unwrap(), None);
        assert!(validate_param(&n, Some("0"), &res).is_err());
        assert!(validate_param(&n, Some("1; reboot"), &res).is_err());
        let _ = std::fs::remove_dir_all(&ws);
    }

    #[test]
    fn fill_is_single_pass() {
        assert_eq!(fill("{a}-{b}", &[("a", "{b}"), ("b", "B")]), "{b}-B");
        assert_eq!(fill("x {unknown} y", &[("a", "1")]), "x {unknown} y");
    }
}
