# llama-gui Design Spec

**Date:** 2026-06-14（初稿）/ 2026-06-19（更新至 v1.0）
**Status:** Implemented (v1.0)
**Author:** brainstormed with user, iterated to completion
**Repo:** https://github.com/Justin-spec-dev/llama-gui

## 1. Overview

A Windows desktop GUI that wraps `llama-server` (from llama.cpp) so the user can
configure parameters, manage presets, start/stop the server, watch resource
usage, and run speed tests — replacing the manual command-line workflow.

### Goals
- Replace the CLI workflow (`llama-server.exe -m ... -c ...`) with a form-driven GUI.
- Fast switching between model configurations via named presets.
- Surface tok/s, CPU, RAM, VRAM, and GPU utilization for empirical parameter tuning.
- Single-developer scope: one user, one Windows machine.

### Non-Goals
- Multi-instance server management (one llama-server at a time).
- Embedded chat UI (out of scope for v1).
- Bundling `llama-server.exe` (user provides).
- Cross-platform support (Windows-only; PySide6 code is portable).

## 2. Tech Stack (Final)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.10+ | PEP 604 union syntax (`int \| None`) |
| GUI | PySide6 (Qt 6.5+) | Native look, rich widgets |
| Theme | Custom QSS | No external theme library; dual light/dark stylesheets built-in |
| Charts | `pyqtgraph` 0.13+ | Real-time rolling plots, 10× lighter than matplotlib |
| System stats | `psutil` 5.9+ + `pynvml` 11.5+ | CPU/RAM via psutil; VRAM/GPU% via pynvml (NVIDIA) |
| HTTP client | `httpx` 0.27+ | Streaming SSE for tok/s benchmark |
| Persistence | `QSettings` (registry) + JSON | Window geometry, theme, last paths → QSettings; presets → `%APPDATA%\llama-gui\presets.json` |
| Packaging | PyInstaller `--onefile` | Single `.exe` with custom `.ico` icon |
| Tests | `pytest` + `pytest-qt` | 40 tests, `core/` has zero PySide6 deps |

## 3. Architecture

```
┌──────────────── llama-gui (PySide6 GUI) ───────────────────┐
│                                                            │
│  MainWindow                                                │
│   ├── MenuBar          文件 / 视图(主题) / 帮助(快捷键)       │
│   ├── ToolBar          ▶启动 ■停止 ↻重启 ●状态灯 预设▼      │
│   ├── TabWidget (7 tabs)                                   │
│   │    ├── 模型         llama-server / model / mmproj       │
│   │    ├── 性能         ngl/ctx/threads/b/ub/cache/flash/...│
│   │    ├── 网络         host/port/api/ui/metrics/alias/jinja│
│   │    ├── 采样         temp/top-k/p/seed/reasoning/...     │
│   │    ├── 高级         split-mode/lora/hf/timeout/...      │
│   │    ├── 监控         速度测试 + CPU/RAM/VRAM/GPU 折线图    │
│   │    └── 预设         保存/加载/重命名/删除                 │
│   ├── LogPanel (底部)   实时日志 stdout/stderr 分色           │
│   └── StatusBar         CPU RAM VRAM GPU 实时数值            │
│                                                            │
│  Business logic (no PySide6) — testable                    │
│   ├── Config dataclass  (40+ fields, None=skip)            │
│   ├── ConfigBuilder     (Config → list[str] argv)           │
│   ├── PresetStore       (JSON atomic write, .bak on corrupt)│
│   ├── ServerProcess     (QProcess + state machine + /health)│
│   ├── ResourceMonitor   (QTimer 1Hz, psutil + pynvml)      │
│   └── SpeedTester       (QRunnable, httpx streaming)       │
│                                                            │
│  Persistence                                                │
│   ├── presets.json        %APPDATA%\llama-gui\              │
│   └── QSettings (HKCU)    window geometry, theme, paths     │
└────────────────────────────────────────────────────────────┘
```

### Design Principles
- **`core/` has zero PySide6 imports** — pure logic, fully unit-testable with plain pytest.
- **Empty/unset = no flag emitted** — the builder skips the flag entirely; llama-server uses its own default.
- **Checkbox semantics match defaults**: llama-default-ON params get "禁用 XXX" labels (check = emit `--no-xxx`), llama-default-OFF params get "启用 XXX" labels (check = emit `--xxx`).

## 4. Key Design Decisions

### 4.1 "Unset = No Flag" Convention

Every widget starts in an "unset" state. Only explicitly configured values get
emitted as CLI flags. Implementation per widget type:

| Widget | Unset state | `values()` returns |
|---|---|---|
| SpinBox | `0` + `specialValueText="(默认 NNN)"` | `spin.value()` if `specialValueText == ""` else `None` |
| DoubleSpinBox | `0.0` + `specialValueText` | Same pattern |
| ComboBox | First item = `"(默认 XXX)"` | `None` if text starts with `"(默认"` |
| "Enable" CheckBox | Unchecked | `True if checked else None` |
| "Disable" CheckBox | Unchecked | `False if checked else None` |
| LineEdit | Empty string | `text or None` |

When user types/changes a value, `specialValueText` is cleared, and `values()`
returns the actual value.

### 4.2 Checkbox Label Convention

| llama default | Checkbox label pattern | Checked emits |
|---|---|---|
| **Enabled** (on) | "禁用 XXX（llama 默认: 启用）" | `--no-xxx` (False) |
| **Disabled** (off) | "启用 XXX（llama 默认: 关闭）" | `--xxx` (True) |

Applied to: `cont_batching`, `enable_ui`, `jinja`, `cache_prompt` (disable-style);
`mlock`, `metrics`, `verbose` (enable-style).

### 4.3 `0.0.0.0` Handling

Background: `0.0.0.0` is a bind address (listen on all interfaces), not a
connect address. Three places were affected and fixed:

| Component | Fix |
|---|---|
| Health check (`/health` polling) | Always `http://127.0.0.1:{port}/health` |
| Speed test (connect to server) | Always `http://127.0.0.1:{port}/v1/chat/completions` |
| Port availability check | Uses `cfg.host or "127.0.0.1"` — works because 127.0.0.1 is always bindable |

### 4.4 Resource Monitor Start Timing

Starts when server enters **LOADING** state (not waiting for READY), so
baseline resource usage is visible immediately after process launch.

## 5. Module Details

### 5.1 `core/config.py`
- `Config`: dataclass with 40+ fields typed as `X | None` (unset) or `bool` (explicit on/off).
- `ConfigBuilder.to_args(cfg)`: converts Config → `list[str]` argv.
  - Skip `None` fields.
  - Boolean `True` → emit flag (e.g. `--mlock`).
  - Boolean `False` on negation fields → emit `--no-*` (e.g. `--no-mmap`).
  - Tri-state (`bool | None`): `True` → positive flag, `False` → negative flag, `None` → skip.
  - String enums validated before emission (`ValueError` on invalid value).
- `enable_ui` is tri-state (`None` = default, `True` = `--ui`, `False` = `--no-ui`).
- `jinja`, `cont_batching`, `cache_prompt` are tri-state.

### 5.2 `core/presets.py`
- `PresetStore`: JSON file in `%APPDATA%\llama-gui\presets.json`.
- Atomic write: temp file → `os.replace()`.
- Corrupt file → rename to `.bak`, reinitialize empty store.
- Methods: `list()`, `get(name)`, `save(preset)`, `delete(name)`, `rename(old, new)`.

### 5.3 `core/process.py`
- `ServerProcess(QObject)`: wraps `QProcess`.
- State machine: `STOPPED → STARTING → LOADING → READY → (STOPPED | ERROR)`.
- Health polling: 500ms interval, `/health` endpoint, 120s timeout.
- `stop()`: `terminate()` → 5s wait → `kill()`.
- Log lines prefixed `[stderr]` / `[CMD]` for color coding.

### 5.4 `core/monitor.py`
- `ResourceMonitor(QObject)`: QTimer 1Hz sampler.
- `psutil`: CPU total%, process CPU%, system RAM, process RSS.
- `pynvml`: GPU utilization%, VRAM used. Graceful fallback to `None` if NVIDIA not available.
- `process_gone` signal on PID exit → MainWindow flips state to ERROR.

### 5.5 `core/speedtest.py`
- `SpeedTester(QObject)`: uses `QRunnable` + `QThreadPool` (non-blocking).
- Connects to `http://127.0.0.1:{port}/v1/chat/completions` with `stream: true`.
- Returns: `{tokens, elapsed_s, first_token_ms, tokens_per_sec}`.
- Pre-check: server must be in READY state; else shows warning dialog.

## 6. Theme System

Custom dual-theme QSS, no external library (no qdarkstyle).

| Component | Light | Dark |
|---|---|---|
| Background | `#f5f5f5` | `#1c1c28` |
| Surface | `#ffffff` | `#222233` |
| Accent | `#3a7abf` | `#4a8abc` |
| Text | `#333` | `#c8c8d0` |
| Tab active | `#dce8f0` | `#1c2c3c` |

- `_BASE_QSS`: shared structural rules (paddings, margins, font families).
- `_DARK_QSS` / `_LIGHT_QSS`: color overrides only.
- Variable substitution (`$border`, `$accent`, `$press`, `$selectedText`) for DRY.
- Global font: 13pt, Segoe UI / Microsoft YaHei, set via `QApplication.setFont()`.
- Menu: 视图 → 主题 → 浅色 / 深色 / 跟随系统.
- "跟随系统" reads `winreg` on Windows.

## 7. Tab Details

### 7.1 模型 (Model)
| Field | Widget | Validation |
|---|---|---|
| llama-server.exe | `PathPicker` (filter: `*.exe`) | Required, must exist |
| 模型 | `PathPicker` (filter: `*.gguf`) | Required, must exist |
| mmproj | `PathPicker` | Optional, must exist if set |

### 7.2 性能 (Performance)
| Flag | Widget | Unset label |
|---|---|---|
| `-ngl` | SpinBox 0–999 | `(默认 auto)` |
| `-ncmoe` | SpinBox 0–999 | `(默认 0)` |
| `-c` | SpinBox 0–1048576 | `(默认 读模型)` |
| `-t` | SpinBox 0–256 | `(默认 自动)` |
| `-tb` | SpinBox 0–256 | `(默认 同 -t)` |
| `-b` | SpinBox 0–4096 | `(默认 2048)` |
| `-ub` | SpinBox 0–4096 | `(默认 512)` |
| `-ctk` | Combo | `(默认 f16)` |
| `-ctv` | Combo | `(默认 f16)` |
| `-fa` | Combo | `(默认 auto)` |
| `--mlock` | CheckBox（启用）| unchecked |
| `--no-mmap` | CheckBox（禁用）| unchecked |
| `-np` | SpinBox 0–64 | `(默认 自动)` |
| `--cont-batching` | CheckBox（禁用）| unchecked (llama default: on) |

### 7.3 网络 (Network)
| Flag | Widget | Unset label |
|---|---|---|
| `--host` | LineEdit | placeholder: `127.0.0.1 (llama 默认)` |
| `--port` | SpinBox 0–65535 | `(默认 8080)` |
| `--api-key` | LineEdit (password) | empty |
| `--ui` | CheckBox（禁用）| unchecked (llama default: on) |
| `--metrics` | CheckBox（启用）| unchecked (llama default: off) |
| `-a` | LineEdit | empty |
| `--jinja` | CheckBox（禁用）| unchecked (llama default: on) |

### 7.4 采样 (Sampling)
| Flag | Widget | Unset label |
|---|---|---|
| `-n` | SpinBox | `(默认 无限)` |
| `--temp` | DoubleSpinBox | `(默认 0.8)` |
| `--top-k` | SpinBox | `(默认 40)` |
| `--top-p` | DoubleSpinBox | `(默认 0.95)` |
| `--min-p` | DoubleSpinBox | `(默认 0.05)` |
| `--repeat-penalty` | DoubleSpinBox | `(默认 1.0)` |
| `--repeat-last-n` | SpinBox | `(默认 64)` |
| `--presence-penalty` | DoubleSpinBox | `(默认 0.0)` |
| `--frequency-penalty` | DoubleSpinBox | `(默认 0.0)` |
| `-s` | SpinBox | `(默认 随机)` |
| `--reasoning` | Combo | `(默认 auto)` |
| `--reasoning-budget` | SpinBox | `(默认 无限)` |

### 7.5 高级 (Advanced)
| Flag | Widget | Unset label |
|---|---|---|
| `-sm` | Combo | `(默认)` |
| `-ts` | LineEdit | empty |
| `-mg` | SpinBox | `(默认)` |
| `--lora` | ListWidget + Add/Remove | empty |
| `--hf-repo` | LineEdit | empty |
| `--hf-file` | LineEdit | empty |
| `--hf-token` | LineEdit (password) | empty |
| `-to` | SpinBox | `(默认 3600s)` |
| `-v` | CheckBox（启用）| unchecked |
| `-lv` | SpinBox 0–5 | `(默认 3)` |
| `--no-warmup` | CheckBox（禁用）| unchecked (llama default: on) |
| `--cache-prompt` | CheckBox（禁用）| unchecked (llama default: on) |

### 7.6 监控 (Monitor)
- Speed test: prompt textbox, start button, result panel (token count, elapsed, first-token ms, tok/s).
- 4 × `pyqtgraph` rolling plots (60-point window, 1Hz): CPU%, RAM GB, VRAM GB, GPU%.
- Plots in 2×2 grid with current-value labels below each plot.
- Speed test pre-check: server must be READY; else shows warning dialog.

### 7.7 预设 (Presets)
- `QListWidget` listing all preset names.
- Double-click or "加载" button → populate all tabs from saved Config.
- "保存当前为预设…" → `QInputDialog` for name → `PresetStore.save()`.
- "重命名…" / "删除" buttons.
- Right side: read-only summary showing server path, model path, ngl, ctx, threads.

## 8. Tooltips

Every widget has a `setToolTip()` with Chinese description based on the
[official llama.cpp server README](https://github.com/ggerganov/llama.cpp/blob/master/tools/server/README.md).
Each tooltip includes: description, llama default value, and relevant notes.

## 9. Log Panel

- `QTextEdit`, read-only, monospace.
- `stdout` → text color from palette; `stderr` → red (`#ff6666` dark / `#cc0000` light).
- `[CMD]` marker → echoes the exact CLI command being executed.
- `[stderr]` prefix → line originated from stderr (checked via `startswith`).
- Max 5000 lines, oldest trimmed from top.
- Toolbar: 清空 / 复制选中.

## 10. Keyboard Shortcuts

| Key | Action | Condition |
|---|---|---|
| `Ctrl+S` | 保存当前为预设 | Always |
| `Ctrl+Enter` | 启动 | Stopped + config valid |
| `F5` | 重启 | Running |
| `Ctrl+.` | 停止 | Running |
| `Ctrl+L` | 清空日志 | Always |
| `Ctrl+Q` | 退出 | Always |
| `F1` | 快捷键帮助 | Always |

## 11. Core Flows

### 11.1 Start
1. User clicks ▶ / `Ctrl+Enter`.
2. Validate: server.exe exists, model.gguf exists, mmproj if set exists.
3. Port check: `socket.bind()` test; if occupied, ask user to confirm.
4. `ConfigBuilder.to_args()` → argv list.
5. Echo `[CMD]` to log.
6. `ServerProcess.start()` with `health_url=http://127.0.0.1:{port}/health`.
7. State machine: STARTING → LOADING → READY (on /health 200) / ERROR (timeout 120s).
8. `ResourceMonitor.start()` on LOADING.

### 11.2 Stop
1. User clicks ■ / `Ctrl+.`.
2. `terminate()` → wait 5s → `kill()`.
3. `ResourceMonitor.stop()`.

### 11.3 Restart (`F5`)
Stop → `SingleShotConnection` to `_on_start_clicked` (no signal leak).

### 11.4 Preset Save (`Ctrl+S`)
1. Prompt for name.
2. Collect Config from all tabs.
3. `PresetStore.save(Preset.now(name, config))`.
4. Refresh combo, select newly saved preset.

### 11.5 Speed Test
1. Check server is READY; else show warning.
2. `SpeedTester.run("127.0.0.1", port, api_key, prompt)` on thread pool.
3. Render result or error.

## 12. Error Handling

| Scenario | Behavior |
|---|---|
| `llama-server.exe` missing at start | Dialog, start blocked |
| Model file missing | Dialog, start blocked |
| Port occupied | Confirm dialog |
| `presets.json` corrupt | Backup to `.bak`, reinitialize |
| `pynvml` not available | GPU/VRAM show "N/A", no error |
| Health timeout (120s) | State → ERROR, stop server |
| Process exits unexpectedly | `process_gone` signal → state ERROR |
| Speed test: server not ready | Warning dialog, no crash |

## 13. Project Structure (Final)

```
llama_app/
├── pyproject.toml
├── pyinstaller.spec
├── README.md
├── .gitignore
├── docs/
│   └── superpowers/
│       ├── specs/2026-06-14-llama-gui-design.md
│       └── plans/2026-06-14-llama-gui.md
├── src/llama_app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── core/
│   │   ├── config.py          # Config dataclass + ConfigBuilder
│   │   ├── validators.py      # Path/port validation
│   │   ├── presets.py         # JSON PresetStore
│   │   ├── process.py         # QProcess ServerProcess
│   │   ├── monitor.py         # psutil + pynvml ResourceMonitor
│   │   └── speedtest.py       # httpx SpeedTester
│   ├── ui/
│   │   ├── main_window.py     # MainWindow (toolbar, tabs, log, statusbar)
│   │   ├── theme.py           # Custom light/dark QSS
│   │   ├── tabs/
│   │   │   ├── model_tab.py
│   │   │   ├── performance_tab.py
│   │   │   ├── network_tab.py
│   │   │   ├── sampling_tab.py
│   │   │   ├── advanced_tab.py
│   │   │   ├── monitor_tab.py
│   │   │   └── presets_tab.py
│   │   └── widgets/
│   │       ├── path_picker.py
│   │       ├── log_panel.py
│   │       ├── status_indicator.py
│   │       └── resource_plot.py
│   └── resources/
│       ├── icon.png
│       └── icon.ico
└── tests/
    ├── conftest.py
    ├── test_config.py         (8 tests)
    ├── test_validators.py     (7 tests)
    ├── test_presets.py        (7 tests)
    ├── test_process.py        (4 tests)
    ├── test_monitor.py        (4 tests)
    ├── test_speedtest.py      (2 tests)
    ├── test_path_picker.py    (3 tests)
    ├── test_log_panel.py      (3 tests)
    └── test_status_indicator.py (2 tests)
```

**Total**: 23 source files + 9 test files = 32 Python files. 40 test cases, all passing.

## 14. Packaging

```bash
pip install pyinstaller pillow
pyinstaller pyinstaller.spec
# → dist/llama-gui.exe (single file, ~90 MB)
```

- Hidden imports: `psutil`, `pynvml`, `httpx`, `pyqtgraph` (added to `.spec`).
- Icon: `icon.ico` (multi-resolution, 16–256px, generated via PIL).
- Does NOT bundle `llama-server.exe` (user provides path via UI).

## 15. Known Bugs Fixed During Development

| Bug | Severity | Root Cause | Fix |
|---|---|---|---|
| NetworkTab dead code | Critical | `alias`/`jinja` widgets created after `return` statement | Rewrote entire file |
| Combo `values()` logic reversed | High | `startswith("(默认")` used without `not` | Added `not` to condition |
| Restart signal leak | High | `QueuedConnection` without disconnect | Changed to `SingleShotConnection` |
| Health check uses `0.0.0.0` | High | Passed `cfg.host` to health URL | Hardcoded `127.0.0.1` |
| Speed test uses `0.0.0.0` | High | Passed `cfg.host` to connect URL | Hardcoded `127.0.0.1` |
| LogPanel hardcoded dark colors | Medium | Light theme unreadable | Palette-based colors |
| SamplingTab `changed` not emitted on 0 | Medium | Lambda ternary skipped emit | Tuple `(emit(), ...)` |
| Log stream misclassification | Medium | `in` instead of `startswith` | Changed to `startswith` |
| `cache_prompt` pre-checked | Medium | `setChecked(True)` in init | Removed |
| PyInstaller missing hidden imports | Medium | `psutil`/`pynvml`/`httpx`/`pyqtgraph` not in `.spec` | Added to `hiddenimports` |

## 16. Acceptance Criteria (All Met)

1. ✅ User can configure all common `llama-server` parameters via the GUI.
2. ✅ User can save/load/rename/delete named presets.
3. ✅ Start/stop/restart with real-time log output and health-check polling.
4. ✅ Resource monitor shows live CPU/RAM/VRAM/GPU% at 1Hz.
5. ✅ Speed test reports tokens/sec, first-token latency, total tokens.
6. ✅ Theme toggle works (light/dark/auto) and persists across restarts.
7. ✅ All keyboard shortcuts functional (`Ctrl+S`, `F5`, `Ctrl+.`, etc.).
8. ✅ Single `.exe` with custom icon produced by PyInstaller.
9. ✅ All 40 pytest tests pass.
10. ✅ Pushed to GitHub with README and .gitignore.
