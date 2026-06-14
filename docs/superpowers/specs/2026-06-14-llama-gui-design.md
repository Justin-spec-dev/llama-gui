# llama-gui Design Spec

**Date:** 2026-06-14
**Status:** Draft — awaiting user approval
**Author:** brainstormed with user

## 1. Overview

A Windows desktop GUI that wraps `llama-server` (from llama.cpp) so the user can
configure parameters, manage presets, start/stop the server, and watch resource
usage — replacing the manual command-line workflow.

### Goals
- Replace the user's current CLI workflow (`llama-server.exe -m ... -c ... ...`)
  with a form-driven GUI.
- Make it fast to switch between model configurations (presets).
- Surface tok/s, CPU, RAM, VRAM, and GPU utilization so the user can tune
  parameters empirically.
- Single-developer scope: one user, one Windows machine.

### Non-Goals
- Multi-instance server management (one llama-server at a time).
- Embedding a chat UI to talk to the model (out of scope for v1).
- Bundling `llama-server.exe` in the installer (user provides it).
- Cross-platform support (Windows-only; PySide6 code is portable, but tests
  and packaging target Windows).

### Target User
Single technical user who already uses `llama-server` from the command line
and wants a more convenient launcher + parameter playground.

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.10+ | User picked PySide6 |
| GUI | PySide6 (Qt 6.5+) | Native look, rich widgets |
| Theme | `qdarkstyle` (light/dark/auto) | Mature, lightweight |
| Charts | `pyqtgraph` | Real-time friendly, 10× lighter than matplotlib |
| System stats | `psutil` + `pynvml` (NVIDIA) | Cross-platform CPU/RAM; pynvml for VRAM/GPU% |
| HTTP client | `httpx` | Streaming support for tok/s test |
| Persistence | `QSettings` (UI state) + JSON file (presets) | Standard, no DB |
| Packaging | PyInstaller (`--onefile --noconsole`) | Single .exe |
| Tests | `pytest` | Standard |

## 3. Architecture

```
┌──────────────── llama-gui (PySide6 GUI) ───────────────────┐
│                                                            │
│  MainWindow                                                │
│   ├── MenuBar          文件/视图/帮助                       │
│   ├── ToolBar          启动/停止/重启 + 状态灯 + 预设下拉    │
│   ├── TabWidget        7 个标签页                           │
│   │    ├── ModelTab       llama-server/model/mmproj        │
│   │    ├── PerformanceTab ngl/ctx/threads/b/ub/cache/...    │
│   │    ├── NetworkTab     host/port/api/ui/alias/...        │
│   │    ├── SamplingTab    temp/top-k/.../reasoning         │
│   │    ├── AdvancedTab    split-mode/lora/hf/...           │
│   │    ├── MonitorTab     速度测试 + 4 个实时折线图          │
│   │    └── PresetsTab     预设管理                          │
│   ├── LogPanel (底部)  实时日志 + 清空/复制/保存             │
│   └── StatusBar        状态灯 + pid + CPU/内存/显存/GPU%     │
│                                                            │
│  Business logic (no PySide6) — testable in isolation        │
│   ├── Config            dataclass holding all flags        │
│   ├── ConfigBuilder     UI fields → Config → list[str] args │
│   ├── PresetStore       load/save/delete Preset in JSON     │
│   ├── ServerProcess     QProcess wrapper: start/stop/log    │
│   ├── ResourceMonitor   psutil + pynvml background sampler  │
│   └── SpeedTester       httpx streaming call to /v1/...    │
│                                                            │
│  Persistence                                                │
│   ├── presets.json        List[Preset]                     │
│   └── QSettings (HKCU)    window geom, theme, last paths    │
└────────────────────────────────────────────────────────────┘
```

### Design Principles
- **`core/` has zero PySide6 imports** — pure logic, fully unit-testable.
- **`ui/` only collects input and displays output** — never assembles
  command-line args, never touches the filesystem directly.
- **Empty fields mean "use llama-server default"** — the builder skips the
  flag entirely so the command line stays clean.

## 4. Module Breakdown

### 4.1 `core/config.py`
```python
@dataclass
class Config:
    # Model
    server_path: str          # required, absolute
    model_path: str           # required, absolute
    mmproj_path: str | None

    # Performance
    n_gpu_layers: int | None   # -ngl
    n_cpu_moe: int | None      # -ncmoe
    ctx_size: int | None       # -c
    threads: int | None        # -t
    threads_batch: int | None  # -tb
    batch_size: int | None     # -b
    ubatch_size: int | None    # -ub
    cache_type_k: str | None   # -ctk
    cache_type_v: str | None   # -ctv
    flash_attn: str | None     # -fa: "on" | "off" | "auto"
    mlock: bool = False
    no_mmap: bool = False
    parallel: int | None       # -np
    cont_batching: bool | None # -cb (None=default, True/False explicit)

    # Network
    host: str | None           # --host
    port: int | None           # --port
    api_key: str | None        # --api-key
    enable_ui: bool = True     # --ui
    metrics: bool = False      # --metrics
    alias: str | None          # -a
    jinja: bool | None         # --jinja (None=default)

    # Sampling
    n_predict: int | None      # -n
    temperature: float | None
    top_k: int | None
    top_p: float | None
    min_p: float | None
    repeat_penalty: float | None
    repeat_last_n: int | None
    presence_penalty: float | None
    frequency_penalty: float | None
    seed: int | None
    reasoning: str | None      # --reasoning: "on" | "off" | "auto"
    reasoning_budget: int | None

    # Advanced (subset shown — full list below)
    split_mode: str | None     # -sm
    tensor_split: str | None   # -ts
    main_gpu: int | None       # -mg
    lora: list[str]            # --lora
    hf_repo: str | None
    hf_file: str | None
    hf_token: str | None
    timeout: int | None        # -to
    verbose: bool = False
    log_verbosity: int | None  # -lv
    no_warmup: bool = False
    cache_prompt: bool | None
    no_cache_prompt: bool = False
    # ... (full list maintained in code)

class ConfigBuilder:
    @staticmethod
    def from_widgets(window) -> Config: ...
    @staticmethod
    def to_args(config: Config) -> list[str]: ...
```

`to_args()` rules:
- Skip `None` fields.
- For booleans, only emit the flag when explicitly `True` (or `False` if
  it's a `--no-*` negation like `--no-mmap`).
- For string enums, validate against allowed values (raise `ValueError` on
  bad input — caller surfaces as UI error).

### 4.2 `core/presets.py`
```python
@dataclass
class Preset:
    name: str
    config: Config
    updated_at: str  # ISO 8601

class PresetStore:
    def __init__(self, path: Path = default_path()): ...
    def list(self) -> list[Preset]: ...
    def get(self, name: str) -> Preset: ...
    def save(self, preset: Preset) -> None: ...
    def delete(self, name: str) -> None: ...
    def rename(self, old: str, new: str) -> None: ...
```

`default_path()` → `%APPDATA%\llama-gui\presets.json`.

Atomic save: write to `presets.json.tmp` then rename.

### 4.3 `core/process.py`
```python
class ServerProcess(QObject):
    state_changed = Signal(str)  # "stopped" | "starting" | "loading" | "ready" | "error"
    log_received = Signal(str)
    pid_changed = Signal(int)

    def start(self, exe: str, args: list[str], cwd: str | None = None) -> None: ...
    def stop(self, timeout_ms: int = 5000) -> None: ...
    def is_running(self) -> bool: ...
    def pid(self) -> int | None: ...
```

- Uses `QProcess` (not `subprocess`) for Qt event-loop integration.
- Polls `/health` after start: 503 → "loading", 200 → "ready".
- On Windows: `stop()` calls `terminate()` first, then `kill()` after 5s.
- Pipes `stdout`/`stderr` to `log_received`.

### 4.4 `core/monitor.py`
```python
class ResourceMonitor(QObject):
    sample = Signal(dict)        # every 1s
    process_gone = Signal()      # emitted when the tracked PID exits

    def __init__(self, get_pid: Callable[[], int | None]): ...
    def start(self) -> None: ...
    def stop(self) -> None: ...

# `process_gone` is wired in MainWindow to flip status to "error" with
# message "Server exited unexpectedly" and stop the monitor.

@dataclass
class Sample:
    cpu_total: float      # %
    cpu_proc: float | None  # %
    mem_total_gb: float
    mem_proc_gb: float | None
    gpu_util: float | None   # %
    vram_gb: float | None
    timestamp: float
```

- `pynvml` initialized once in `__init__`; failure → `gpu_util` and `vram_gb`
  always `None` (UI shows "N/A").
- PID lookup: if `pid` invalid or dead, `cpu_proc`/`mem_proc_gb` are `None`
  and a `process_gone` signal is emitted.

### 4.5 `core/speedtest.py`
```python
class SpeedTester(QObject):
    finished = Signal(dict)  # {tokens, elapsed_s, first_token_ms, tokens_per_sec}
    failed = Signal(str)

    def run(self, host: str, port: int, api_key: str | None, prompt: str,
            max_tokens: int = 200) -> None: ...
```

Runs `httpx.stream("POST", ...)` against `/v1/chat/completions` with
`"stream": true`. Counts SSE chunks and measures first-token latency.
Runs in a worker thread (via `QThreadPool`).

## 5. UI Layout

### 5.1 Main Window

```
┌─ llama-gui ─────────────────────────────────────────────────────┐
│ 文件  视图  帮助                                                  │
├──────────────────────────────────────────────────────────────────┤
│ [▶ 启动] [■ 停止] [↻ 重启]  ●绿  预设:[Qwen 32B 8K      ▼]      │
├──────────────────────────────────────────────────────────────────┤
│ ┌─Model─┬─Performance─┬─Network─┬─Sampling─┬─Advanced─┬─...─┐  │
│ │       │             │         │          │          │     │  │
│ │       │             │         │          │          │     │  │
│ │       │             │         │          │          │     │  │
│ ├───────┴─────────────┴─────────┴──────────┴──────────┴─────┤  │
│ │ [Log] llama-server output streaming here...                │  │
│ │       [清空] [复制] [保存到文件]                            │  │
│ └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│ ●绿 pid=1234  CPU 45%  RAM 8.2G  VRAM 6.1G  GPU 87%             │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Tab Contents

#### Tab 1: Model
| Field | Widget | Validation |
|---|---|---|
| llama-server.exe | PathPicker | required, file exists, .exe |
| 模型 (Model) | PathPicker | required, file exists, .gguf |
| mmproj | PathPicker | optional, file exists, .gguf |

#### Tab 2: Performance
| Flag | Widget | Range / Options |
|---|---|---|
| `--n-gpu-layers` (`-ngl`) | SpinBox | 0–999, default 0 |
| `--n-cpu-moe` (`-ncmoe`) | SpinBox | 0–999 |
| `--ctx-size` (`-c`) | SpinBox | 128–1048576 |
| `--threads` (`-t`) | SpinBox | 1–256 |
| `--threads-batch` (`-tb`) | SpinBox | 1–256 |
| `--batch-size` (`-b`) | SpinBox | 1–4096 |
| `--ubatch-size` (`-ub`) | SpinBox | 1–4096 |
| `--cache-type-k` (`-ctk`) | Combo | f16/f32/bf16/q8_0/q4_0/q4_1/iq4_nl/q5_0/q5_1 |
| `--cache-type-v` (`-ctv`) | Combo | same |
| `--flash-attn` (`-fa`) | Combo | on / off / auto (default auto) |
| `--mlock` | CheckBox | |
| `--no-mmap` | CheckBox | |
| `--parallel` (`-np`) | SpinBox | 1–64 |
| `--cont-batching` (`-cb`) | CheckBox (3-state) | checked=on, unchecked=off, partial=default |

#### Tab 3: Network
| Flag | Widget | Default |
|---|---|---|
| `--host` | LineEdit | 127.0.0.1 |
| `--port` | SpinBox | 8080 |
| `--api-key` | LineEdit (password) | empty |
| `--ui` (Web UI) | CheckBox | checked |
| `--metrics` | CheckBox | unchecked |
| `-a, --alias` | LineEdit | empty |
| `--jinja` / `--no-jinja` | CheckBox (3-state) | partial=default |

#### Tab 4: Sampling
| Flag | Widget | Default |
|---|---|---|
| `-n, --n-predict` | SpinBox | -1=∞ |
| `--temp` | DoubleSpin | 0.80 |
| `--top-k` | SpinBox | 40 |
| `--top-p` | DoubleSpin | 0.95 |
| `--min-p` | DoubleSpin | 0.05 |
| `--repeat-penalty` | DoubleSpin | 1.00 |
| `--repeat-last-n` | SpinBox | 64 |
| `--presence-penalty` | DoubleSpin | 0.00 |
| `--frequency-penalty` | DoubleSpin | 0.00 |
| `--seed` | SpinBox | -1=random |
| `--reasoning` | Combo | on / off / auto |
| `--reasoning-budget` | SpinBox | -1=∞ |

#### Tab 5: Advanced
| Flag | Widget |
|---|---|
| `-sm, --split-mode` | Combo: none / layer / row / tensor |
| `-ts, --tensor-split` | LineEdit (comma-sep) |
| `-mg, --main-gpu` | SpinBox |
| `--lora` | List + Add/Remove buttons |
| `--hf-repo` | LineEdit |
| `--hf-file` | LineEdit |
| `--hf-token` | LineEdit (password) |
| `-to, --timeout` | SpinBox (seconds) |
| `--verbose` | CheckBox |
| `-lv, --log-verbosity` | SpinBox 0–5 |
| `--no-warmup` | CheckBox |
| `--cache-prompt` / `--no-cache-prompt` | CheckBox (3-state) |

(Other advanced flags can be added in this tab as the user discovers them.)

#### Tab 6: Monitor
- Top section: speed test (prompt textbox, run button, result panel).
- Middle: 4 pyqtgraph plots in a 2×2 grid (CPU%, RAM GB, VRAM GB, GPU%),
  each with current-value label below.
- Bottom: "导出 CSV" button to dump the in-memory sample buffer.

#### Tab 7: Presets
- `QListWidget` (left) with preset names.
- Buttons: 保存当前为预设 / 加载 / 重命名 / 删除.
- Right side: read-only summary of selected preset (key params only).

### 5.3 Log Panel
- Monospace font, dark background (in light theme: also dark for readability).
- Max 5000 lines, older lines dropped from top.
- Toolbar: 清空 / 复制选中 / 保存到文件 (.log).
- Color: stderr lines in red, stdout in default, `[CMD]` echo of launch
  command in cyan.
- Timestamps: each line prefixed with `HH:MM:SS`; toggle on/off via toolbar
  checkbox.

### 5.4 Status Bar
Always visible, format:
```
[●] 运行中 pid=1234  |  CPU 45%  RAM 8.2G  VRAM 6.1G  GPU 87%
```
Updates 1Hz from `ResourceMonitor`. When stopped: `[○] 已停止`.

## 6. Core Flows

### 6.1 Start
1. User clicks ▶ 启动 (or presses `Ctrl+Enter`).
2. `ConfigBuilder.from_widgets(window)` builds `Config`.
3. Validate: `server_path` and `model_path` exist; `mmproj` (if set) exists;
   `port` not in use (`socket.bind` test, skip-able by setting
   `settings.skip_port_check = True`).
4. Build `args = ConfigBuilder.to_args(config)`.
5. Echo `[CMD] "C:\...\llama-server.exe" -m "..." -c 8192 ...` to log.
6. `ServerProcess.start(exe, args, cwd=dirname(model))`.
7. State → "starting" → "loading" (on process up) → "ready" (on `/health` 200).
8. `ResourceMonitor.start()` (uses new pid).
9. On any error: state → "error", show dialog, status bar red.

### 6.2 Stop
1. User clicks ■ 停止 (or presses `Ctrl+.`).
2. `ServerProcess.stop()` → `terminate()`.
3. Wait up to 5s for process exit; else `kill()`.
4. `ResourceMonitor.stop()`.
5. State → "stopped", status bar grey.

### 6.3 Restart (F5)
Equivalent to stop → wait → start, with same config.

### 6.4 Preset Save
1. User presses `Ctrl+S` or clicks 保存当前为预设.
2. `QInputDialog.getText` for name (default: timestamp).
3. `PresetStore.save(Preset(name, current_config, now_iso))`.
4. Refresh Preset list.

### 6.5 Preset Load
1. User selects preset, clicks 加载 (or double-clicks).
2. `PresetStore.get(name)` → `Config`.
3. Each Tab widget updated from Config (with `blockSignals(True)` to avoid
   spurious dirty flags).
4. Status bar message: "已加载预设 'XXX'".

### 6.6 Speed Test
1. User edits prompt, clicks ▶ 开始测试.
2. Pre-check: server is "ready".
3. `SpeedTester.run(host, port, api_key, prompt)` in worker thread.
4. On `finished`: render result (tokens, elapsed, first-token ms, tok/s).
5. On `failed`: show error in result panel.

## 7. Theme

- Library: `qdarkstyle`.
- Menu: 视图 → 主题 → [○ 浅色 | ● 深色 | ○ 跟随系统].
- "跟随系统" reads `darkdetect.isDark()` (lightweight lib) or `QPalette`.
- Theme stored in `QSettings.ui/theme`.
- Applied in `MainWindow.__init__` after `QApplication` created.

## 8. Keyboard Shortcuts

| Key | Action | Conditions |
|---|---|---|
| `Ctrl+S` | 保存当前为预设 | always |
| `Ctrl+Enter` | 启动 | stopped + config valid |
| `F5` | 重启 | running |
| `Ctrl+.` | 停止 | running |
| `Ctrl+L` | 清空日志 | always |
| `Ctrl+C` (in log panel) | 复制选中 | log has selection |
| `Ctrl+Q` | 退出 | always |
| `F1` | 快捷键帮助 | always |

All registered as `QAction`s in `MainWindow` (they auto-appear in menus and
carry tooltip hints).

## 9. Error Handling

| Scenario | Behavior |
|---|---|
| `llama-server.exe` missing | Red text under field, start button disabled |
| Model file missing | Same |
| Port in use at start | Dialog: "Port 8080 is in use. Change port and retry?" |
| Server fails to start (crash within 3s) | Red state, dialog with last 30 log lines |
| Server becomes unresponsive (health fails 30s) | Red state, "Server unresponsive" |
| `presets.json` corrupt on load | Backup to `.bak`, dialog: "Presets file was corrupt — restored to empty. Backup at presets.json.bak." |
| `pynvml` init fails (no NVIDIA) | GPU/VRAM widgets show "N/A" — no error |
| Path contains spaces / Chinese | QProcess receives `list[str]` — Windows quoting handled by Qt, no manual escaping needed |

## 10. Persistence

- **Window geometry**: `QSettings` keys `window/x`, `window/y`, `window/w`,
  `window/h`, `window/maximized`. Restored on startup.
- **Theme**: `QSettings.ui/theme`.
- **Last llama-server.exe path**: `QSettings.paths/last_server_exe`.
- **Last loaded preset name**: `QSettings.presets/last_loaded`. Auto-loaded
  on startup if it still exists.
- **Presets**: `presets.json` in `%APPDATA%\llama-gui\`.
- **Window state (tab index, etc.)**: optional, low priority.

## 11. Project Structure

```
llama_app/
├── pyproject.toml
├── README.md
├── src/
│   └── llama_app/
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── core/                   # NO PySide6 imports here
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── presets.py
│       │   ├── process.py
│       │   ├── monitor.py
│       │   ├── speedtest.py
│       │   └── validators.py
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── tabs/
│       │   │   ├── __init__.py
│       │   │   ├── model_tab.py
│       │   │   ├── performance_tab.py
│       │   │   ├── network_tab.py
│       │   │   ├── sampling_tab.py
│       │   │   ├── advanced_tab.py
│       │   │   ├── monitor_tab.py
│       │   │   └── presets_tab.py
│       │   └── widgets/
│       │       ├── __init__.py
│       │       ├── path_picker.py
│       │       ├── log_panel.py
│       │       ├── status_indicator.py
│       │       └── resource_plot.py
│       │
│       └── resources/
│           └── strings.json
│
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_presets.py
    ├── test_validators.py
    ├── test_process.py
    └── test_speedtest.py
```

## 12. Testing Strategy

| Level | Tool | Coverage |
|---|---|---|
| Unit | `pytest` | `ConfigBuilder.to_args` for all fields, all combinations of empty/default/explicit; `PresetStore` round-trip; validators |
| Integration | `pytest` + `QProcess` (mocked) | `ServerProcess` state transitions, log streaming |
| Manual | — | UI flow, theme switch, resolution, edge cases (long paths, non-ASCII) |

CI runs unit tests on every commit. Integration tests run on demand
(marked `@pytest.mark.integration`).

## 13. Packaging

- **PyInstaller**: `pyinstaller --noconsole --onefile --name llama-gui src/llama_app/__main__.py`
- Result: single `llama-gui.exe`, no DLL dependencies beyond system + VC runtime.
- Does **not** bundle `llama-server.exe` (user provides).
- README includes: download `llama.cpp` release ZIP, extract `llama-server.exe`
  somewhere, point llama-gui at it.
- Code signing: out of scope for v1 (user accepts SmartScreen warning).

## 14. Open Questions / Future Work

- Code signing certificate.
- Auto-update check.
- Export/import presets across machines.
- Built-in chat panel (out of scope per Section 1).
- Linux/macOS port (PySide6 code is portable, but packaging differs).

## 15. Acceptance Criteria

The project is "done enough" for v1 when:

1. User can configure all common `llama-server` parameters via the GUI.
2. User can save/load/rename/delete named presets.
3. Clicking 启动 launches `llama-server.exe` with the right args and shows
   its output in the log panel.
4. Clicking 停止 terminates the server cleanly.
5. Resource monitor shows live CPU/RAM/VRAM/GPU% and updates at ≥1Hz.
6. Speed test reports tokens/sec, first-token latency, total tokens.
7. Theme toggle works (light/dark/auto) and persists across restarts.
8. All keyboard shortcuts in Section 8 work as specified.
9. Single `.exe` produced by PyInstaller runs on a clean Windows 10/11 box
   with only the VC++ runtime installed.
10. `pytest` passes for the `core/` layer.
