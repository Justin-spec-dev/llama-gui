# UI Workbench Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the selected Navigation Workbench UI while fixing the reviewed lifecycle, security, preset-recovery, monitoring, and speed-measurement defects.

**Architecture:** Keep `Config` and the existing page widgets as the data model and form source. Add small UI shell components around them, move display-command formatting into pure core code, and make `ServerProcess` the sole owner of asynchronous start/stop/restart/health behavior. `MainWindow` remains the composition root but no longer reaches into private members.

**Tech Stack:** Python 3.10+, PySide6 6.5+, pyqtgraph, psutil, nvidia-ml-py, httpx, pytest, pytest-qt, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-06-19-ui-workbench-optimization-design.md`

---

## File Structure

### New files

- `src/llama_app/core/command.py` — safe display formatting and sensitive-argument redaction.
- `src/llama_app/ui/widgets/navigation_rail.py` — section navigation and compact resource summary.
- `src/llama_app/ui/widgets/command_bar.py` — persistent preset/model/status/lifecycle controls.
- `src/llama_app/ui/widgets/config_page.py` — scroll wrapper and reusable section heading.
- `tests/test_command.py` — command formatting/redaction tests.
- `tests/test_navigation_rail.py` — navigation and resource-summary tests.
- `tests/test_command_bar.py` — lifecycle presentation tests.
- `tests/test_main_window.py` — integration, dirty-state, and minimum-size tests.

### Modified files

- `src/llama_app/core/config.py` — cross-field validation.
- `src/llama_app/core/presets.py` — corruption recovery and secret omission.
- `src/llama_app/core/process.py` — asynchronous lifecycle, restart, health, and exit classification.
- `src/llama_app/core/monitor.py` — stable process CPU sampling and NVML cleanup.
- `src/llama_app/core/speedtest.py` — structured SSE parsing and count-source reporting.
- `src/llama_app/ui/main_window.py` — assemble the workbench shell and remove private-member access.
- `src/llama_app/ui/theme.py` — workbench states, focus visibility, typography, and light/dark colors.
- `src/llama_app/ui/tabs/*.py` — public page APIs, grouping, explicit-default behavior, and accessibility labels.
- `src/llama_app/ui/widgets/log_panel.py` — filtering, auto-scroll, record cap, and theme refresh.
- `src/llama_app/ui/widgets/status_indicator.py` — text-first status presentation.
- `pyproject.toml` and `pyinstaller.spec` — supported NVML distribution dependency.
- Existing tests — regression coverage and API updates.

---

## Task 1: Safe Command Display and Cross-Field Validation

**Files:**
- Create: `src/llama_app/core/command.py`
- Create: `tests/test_command.py`
- Modify: `src/llama_app/core/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing redaction tests**

```python
from llama_app.core.command import format_display_command


def test_display_command_redacts_sensitive_values():
    text = format_display_command(
        r"C:\Program Files\llama\llama-server.exe",
        ["-m", r"C:\Models\a model.gguf", "--api-key", "secret-a", "--hf-token", "secret-b"],
    )
    assert "secret-a" not in text
    assert "secret-b" not in text
    assert text.count("********") == 2
    assert '"C:\\Program Files\\llama\\llama-server.exe"' in text


def test_display_command_keeps_real_arguments_unchanged():
    args = ["--api-key", "secret-a"]
    format_display_command("llama-server.exe", args)
    assert args == ["--api-key", "secret-a"]
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_command.py -v`  
Expected: collection fails with `ModuleNotFoundError: llama_app.core.command`.

- [ ] **Step 3: Implement display formatting**

```python
"""Formatting helpers for commands shown to users."""
from __future__ import annotations

import subprocess
from collections.abc import Sequence

_SENSITIVE_FLAGS = frozenset({"--api-key", "--hf-token"})


def redact_args(arguments: Sequence[str]) -> list[str]:
    safe = list(arguments)
    for index, value in enumerate(safe[:-1]):
        if value in _SENSITIVE_FLAGS:
            safe[index + 1] = "********"
    return safe


def format_display_command(program: str, arguments: Sequence[str]) -> str:
    return subprocess.list2cmdline([program, *redact_args(arguments)])
```

- [ ] **Step 4: Add failing cross-field tests**

```python
import pytest
from llama_app.core.config import Config


def test_config_rejects_ubatch_larger_than_batch():
    cfg = Config("server.exe", "model.gguf", batch_size=256, ubatch_size=512)
    with pytest.raises(ValueError, match="ubatch_size"):
        cfg.validate()


def test_config_rejects_blank_required_paths():
    with pytest.raises(ValueError, match="server_path"):
        Config("", "model.gguf").validate()
```

- [ ] **Step 5: Implement focused validation**

Add to `Config.validate()` after enum validation:

```python
        if not self.server_path.strip():
            raise ValueError("server_path is required")
        if not self.model_path.strip():
            raise ValueError("model_path is required")
        if (
            self.batch_size is not None
            and self.ubatch_size is not None
            and self.ubatch_size > self.batch_size
        ):
            raise ValueError("ubatch_size must be less than or equal to batch_size")
```

- [ ] **Step 6: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_command.py tests/test_config.py -v`  
Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add src/llama_app/core/command.py src/llama_app/core/config.py tests/test_command.py tests/test_config.py
git commit -m "fix: redact secrets and validate config relationships"
```

## Task 2: Resilient, Secret-Free Presets

**Files:**
- Modify: `src/llama_app/core/presets.py`
- Modify: `tests/test_presets.py`

- [ ] **Step 1: Write failing recovery and secret tests**

```python
import json
from llama_app.core.config import Config
from llama_app.core.presets import Preset, PresetStore


def test_corrupt_store_recovers_empty_and_keeps_backup(tmp_path):
    path = tmp_path / "presets.json"
    path.write_text("{bad json", encoding="utf-8")
    store = PresetStore(path)
    assert store.list() == []
    assert store.recovery_notice is not None
    assert (tmp_path / "presets.json.bak").exists()
    assert json.loads(path.read_text(encoding="utf-8"))["presets"] == []


def test_saved_preset_omits_secrets(tmp_path):
    path = tmp_path / "presets.json"
    store = PresetStore(path)
    cfg = Config("server.exe", "model.gguf", api_key="api-secret", hf_token="hf-secret")
    store.save(Preset.now("safe", cfg))
    text = path.read_text(encoding="utf-8")
    assert "api-secret" not in text
    assert "hf-secret" not in text
    loaded = store.get("safe").config
    assert loaded.api_key is None
    assert loaded.hf_token is None
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_presets.py -v`  
Expected: corrupt-store test raises `ValueError`; secret test finds plaintext values.

- [ ] **Step 3: Implement recovery and sanitization**

Add imports and helpers:

```python
from dataclasses import asdict, dataclass, replace


def _without_secrets(config: Config) -> Config:
    return replace(config, api_key=None, hf_token=None)
```

Initialize `self.recovery_notice: str | None = None`, parse through a helper, and recover all structural errors:

```python
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            entries = data.get("presets", [])
            if not isinstance(entries, list):
                raise ValueError("presets must be a list")
            self._presets = {
                entry["name"]: Preset(
                    name=entry["name"],
                    config=Config(**entry["config"]),
                    updated_at=entry["updated_at"],
                )
                for entry in entries
            }
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            backup = self.path.with_suffix(self.path.suffix + ".bak")
            self.path.replace(backup)
            self._presets = {}
            self.recovery_notice = f"Recovered corrupt presets; backup: {backup}; error: {exc}"
            self._save_atomic()
```

Sanitize at the store boundary:

```python
    def save(self, preset: Preset) -> None:
        safe = Preset(
            name=preset.name,
            config=_without_secrets(preset.config),
            updated_at=preset.updated_at,
        )
        self._presets[safe.name] = safe
        self._save_atomic()
```

- [ ] **Step 4: Verify GREEN and compatibility**

Run: `.venv\Scripts\python.exe -m pytest tests/test_presets.py -v`  
Expected: all preset tests pass; update the old corruption test to assert recovery instead of an exception.

- [ ] **Step 5: Commit**

```powershell
git add src/llama_app/core/presets.py tests/test_presets.py
git commit -m "fix: recover presets and omit stored secrets"
```

## Task 3: Accurate Streaming Speed Results

**Files:**
- Modify: `src/llama_app/core/speedtest.py`
- Modify: `tests/test_speedtest.py`
- Modify: `src/llama_app/ui/tabs/monitor_tab.py`

- [ ] **Step 1: Write failing parser tests**

```python
from llama_app.core.speedtest import parse_sse_event


def test_parse_sse_event_ignores_role_and_empty_content():
    assert parse_sse_event('data: {"choices":[{"delta":{"role":"assistant"}}]}') == (0, None)
    assert parse_sse_event('data: {"choices":[{"delta":{"content":""}}]}') == (0, None)


def test_parse_sse_event_counts_content_and_usage():
    assert parse_sse_event('data: {"choices":[{"delta":{"content":"hello"}}]}') == (1, None)
    assert parse_sse_event('data: {"choices":[],"usage":{"completion_tokens":12}}') == (0, 12)
```

- [ ] **Step 2: Run the parser tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_speedtest.py -v`  
Expected: import fails because `parse_sse_event` does not exist.

- [ ] **Step 3: Implement structured parsing**

```python
def parse_sse_event(line: str) -> tuple[int, int | None]:
    if not line.startswith("data: ") or line == "data: [DONE]":
        return 0, None
    try:
        event = json.loads(line[6:])
    except json.JSONDecodeError:
        return 0, None
    usage = event.get("usage") or {}
    usage_tokens = usage.get("completion_tokens")
    content_chunks = 0
    for choice in event.get("choices") or []:
        content = (choice.get("delta") or {}).get("content")
        if content:
            content_chunks += 1
    return content_chunks, usage_tokens if isinstance(usage_tokens, int) else None
```

In `_run_speed_test`, request streamed usage, count only non-empty content, and prefer the final usage value:

```python
    payload["stream_options"] = {"include_usage": True}
    content_chunks = 0
    usage_tokens: int | None = None
    # inside iter_lines
    added, reported = parse_sse_event(line)
    if added and t_first is None:
        t_first = time.perf_counter() - t_start
    content_chunks += added
    if reported is not None:
        usage_tokens = reported
    # after stream
    tokens = usage_tokens if usage_tokens is not None else content_chunks
    count_source = "usage" if usage_tokens is not None else "content_chunks"
```

Return `count_source` in the result dictionary.

- [ ] **Step 4: Update result presentation**

Use a public API on `MonitorTab`:

```python
    def prompt_text(self) -> str:
        return self._prompt.toPlainText()

    def set_test_pending(self, pending: bool) -> None:
        self._run_btn.setEnabled(not pending)
        if pending:
            self._result.setPlainText("测试中…")

    def show_test_result(self, result: dict) -> None:
        self.set_test_pending(False)
        label = "Tokens" if result["count_source"] == "usage" else "流式内容块（估算）"
        self._result.setPlainText(
            f"{label}: {result['tokens']}\n"
            f"耗时: {result['elapsed_s']:.2f} s\n"
            f"首 token 延迟: {result['first_token_ms']:.0f} ms\n"
            f"平均速度: {result['tokens_per_sec']:.1f} tokens/s"
        )

    def show_test_error(self, message: str) -> None:
        self.set_test_pending(False)
        self._result.setPlainText(f"测试失败: {message}")
```

Render `Tokens` when `count_source == "usage"`; otherwise render `流式内容块（估算）` so fallback data is not mislabeled.

- [ ] **Step 5: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_speedtest.py -v`  
Expected: all speed-test tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/llama_app/core/speedtest.py src/llama_app/ui/tabs/monitor_tab.py tests/test_speedtest.py
git commit -m "fix: report structured speed test results"
```

## Task 4: Non-Blocking Server Lifecycle and Reliable Restart

**Files:**
- Modify: `src/llama_app/core/process.py`
- Modify: `tests/test_process.py`

- [ ] **Step 1: Write failing lifecycle tests**

Add tests that use `sys.executable` as the child process:

```python
def test_stop_returns_without_waiting_for_process(qtbot):
    p = ServerProcess()
    p.start(sys.executable, ["-c", "import time; time.sleep(10)"])
    qtbot.waitUntil(p.is_running, timeout=3000)
    started = time.perf_counter()
    p.stop(timeout_ms=100)
    assert time.perf_counter() - started < 0.2
    qtbot.waitUntil(lambda: p.state == ServerState.STOPPED, timeout=3000)


def test_unexpected_nonzero_exit_is_error(qtbot):
    p = ServerProcess()
    p.start(sys.executable, ["-c", "raise SystemExit(7)"])
    qtbot.waitUntil(lambda: p.state in {ServerState.ERROR, ServerState.STOPPED}, timeout=3000)
    assert p.state == ServerState.ERROR


def test_restart_starts_exactly_one_replacement(qtbot):
    p = ServerProcess()
    p.start(sys.executable, ["-c", "import time; time.sleep(10)"])
    qtbot.waitUntil(p.is_running, timeout=3000)
    started_pids = []
    p.pid_changed.connect(lambda pid: started_pids.append(pid) if pid else None)
    p.restart(sys.executable, ["-c", "import time; time.sleep(10)"], stop_timeout_ms=100)
    qtbot.waitUntil(lambda: len(started_pids) == 1 and p.is_running(), timeout=5000)
    assert len(started_pids) == 1
    p.stop(timeout_ms=100)
```

- [ ] **Step 2: Run lifecycle tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_process.py -v`  
Expected: blocking-stop timing fails, unexpected exit is `STOPPED`, and `restart` is missing.

- [ ] **Step 3: Add launch specification and non-blocking stop**

```python
from dataclasses import dataclass
from PySide6.QtCore import QProcess, QTimer


@dataclass(frozen=True)
class LaunchSpec:
    program: str
    arguments: tuple[str, ...]
    cwd: str | None = None
    health_url: str | None = None
    health_timeout_s: int = 30
```

Create one single-shot kill timer in `__init__`:

```python
        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.timeout.connect(self._force_kill)
        self._stop_requested = False
        self._error_latched = False
        self._restart_spec: LaunchSpec | None = None
```

Replace blocking stop and add restart:

```python
    def stop(self, timeout_ms: int = 5000) -> None:
        if not self.is_running():
            return
        self._stop_requested = True
        self._stop_health_check()
        self._proc.terminate()
        self._kill_timer.start(timeout_ms)

    def restart(self, program: str, arguments: list[str], *, cwd: str | None = None,
                health_url: str | None = None, health_timeout_s: int = 30,
                stop_timeout_ms: int = 5000) -> None:
        self._restart_spec = LaunchSpec(program, tuple(arguments), cwd, health_url, health_timeout_s)
        if self.is_running():
            self.stop(stop_timeout_ms)
        else:
            spec, self._restart_spec = self._restart_spec, None
            self._start_spec(spec)

    def _force_kill(self) -> None:
        if self.is_running():
            self._proc.kill()
```

- [ ] **Step 4: Classify exits and run one pending restart**

```python
    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._kill_timer.stop()
        self._flush_buffers()
        requested = self._stop_requested
        self._stop_requested = False
        pending, self._restart_spec = self._restart_spec, None
        if pending is not None:
            self._set_state(ServerState.STOPPED)
            QTimer.singleShot(0, lambda spec=pending: self._start_spec(spec))
        elif self._error_latched:
            self._set_state(ServerState.ERROR)
        elif requested:
            self._set_state(ServerState.STOPPED)
        else:
            self.log_received.emit(f"[error] process exited: code={exit_code}, status={exit_status}")
            self._set_state(ServerState.ERROR)
        self.pid_changed.emit(0)
```

Extract the existing buffer loop without changing its behavior:

```python
    def _flush_buffers(self) -> None:
        for attr, is_stderr in (("_stdout_buf", False), ("_stderr_buf", True)):
            remaining = getattr(self, attr)
            if remaining:
                prefix = "[stderr] " if is_stderr else ""
                self.log_received.emit(prefix + remaining)
                setattr(self, attr, "")
```

`_on_error()` sets `_error_latched = True` before entering `ERROR`. Health timeout does the same before requesting stop. `start()` constructs a `LaunchSpec` and delegates to `_start_spec()`. `_start_spec()` clears `_error_latched` and stop flags, configures health state before starting, and starts the process.

- [ ] **Step 5: Replace blocking health requests with `QNetworkAccessManager`**

Initialize a manager and track one active reply:

```python
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

        self._network = QNetworkAccessManager(self)
        self._health_reply: QNetworkReply | None = None
```

Issue one asynchronous request per timer tick:

```python
    def _check_health(self) -> None:
        if not self._health_url or self._health_reply is not None:
            return
        if time.monotonic() > self._health_deadline:
            self.log_received.emit("[health] timeout: server did not become ready")
            self._set_state(ServerState.ERROR)
            self.stop()
            return
        request = QNetworkRequest(QUrl(self._health_url))
        request.setTransferTimeout(1000)
        self._health_reply = self._network.get(request)
        self._health_reply.finished.connect(self._on_health_reply)

    def _on_health_reply(self) -> None:
        reply, self._health_reply = self._health_reply, None
        if reply is None:
            return
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        reply.deleteLater()
        if isinstance(status, int) and 200 <= status < 300:
            self._set_state(ServerState.READY)
            self._stop_health_check()
```

`_stop_health_check()` stops the timer and aborts/deletes an active reply.

- [ ] **Step 6: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_process.py -v`  
Expected: all process tests pass without UI-thread waits.

- [ ] **Step 7: Commit**

```powershell
git add src/llama_app/core/process.py tests/test_process.py
git commit -m "fix: make server lifecycle asynchronous"
```

## Task 5: Stable Resource Sampling and Supported NVML Package

**Files:**
- Modify: `src/llama_app/core/monitor.py`
- Modify: `tests/test_monitor.py`
- Modify: `pyproject.toml`
- Modify: `pyinstaller.spec`

- [ ] **Step 1: Write a failing process-cache test**

```python
def test_monitor_reuses_process_for_cpu_delta(monkeypatch, qtbot):
    created = []

    class FakeProcess:
        def __init__(self, pid):
            created.append(pid)
        def cpu_percent(self): return 12.5
        def memory_info(self): return type("M", (), {"rss": 1024 ** 3})()

    monkeypatch.setattr(psutil, "Process", FakeProcess)
    monkeypatch.setattr(psutil, "pid_exists", lambda _pid: True)
    monitor = ResourceMonitor(lambda: 42)
    monitor._sample()
    monitor._sample()
    assert created == [42]


def test_monitor_uses_requested_gpu_index(monkeypatch):
    requested = []
    fake_nvml = type("NVML", (), {
        "nvmlDeviceGetHandleByIndex": lambda _self, index: requested.append(index) or object(),
    })()
    monitor = ResourceMonitor(lambda: None, gpu_index=2, nvml=fake_nvml)
    assert requested == [2]
```

- [ ] **Step 2: Run the monitor tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_monitor.py -v`  
Expected: `created == [42, 42]`.

- [ ] **Step 3: Cache the process by PID and shut down NVML**

```python
        self._process = None
        self._process_pid: int | None = None

    def _process_for_pid(self, pid: int, psutil):
        if self._process is None or self._process_pid != pid:
            self._process = psutil.Process(pid)
            self._process_pid = pid
            self._process.cpu_percent()
        return self._process
```

Add `gpu_index: int = 0` and an optional injected `nvml` test seam to the constructor. Use the requested index for `nvmlDeviceGetHandleByIndex(gpu_index)`. Use `_process_for_pid()` in `_sample()`, clear the cache when the PID disappears, and call `nvmlShutdown()` once in `stop()` when initialized, catching NVML errors. `MainWindow` passes `cfg.main_gpu or 0` when starting the monitor.

- [ ] **Step 4: Migrate the distribution name**

In `pyproject.toml`, replace:

```toml
"pynvml>=11.5",
```

with:

```toml
"nvidia-ml-py>=12.0",
```

Keep the import/hidden import name `pynvml`, because that is the module exported by `nvidia-ml-py`.

- [ ] **Step 5: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_monitor.py -v`  
Expected: all monitor tests pass without a `pynvml` distribution deprecation warning after reinstalling the editable package.

- [ ] **Step 6: Commit**

```powershell
git add src/llama_app/core/monitor.py tests/test_monitor.py pyproject.toml pyinstaller.spec
git commit -m "fix: stabilize resource monitoring"
```

## Task 6: Navigation Workbench Shell Components

**Files:**
- Create: `src/llama_app/ui/widgets/navigation_rail.py`
- Create: `src/llama_app/ui/widgets/command_bar.py`
- Create: `src/llama_app/ui/widgets/config_page.py`
- Create: `tests/test_navigation_rail.py`
- Create: `tests/test_command_bar.py`
- Create: `tests/test_config_page.py`
- Modify: `src/llama_app/__main__.py`
- Modify: `src/llama_app/ui/theme.py`

- [ ] **Step 1: Write failing navigation tests**

```python
from llama_app.ui.widgets.navigation_rail import NavigationRail


def test_navigation_rail_emits_page_key(qtbot):
    rail = NavigationRail()
    qtbot.addWidget(rail)
    with qtbot.waitSignal(rail.page_selected) as blocker:
        rail.select_page("network")
    assert blocker.args == ["network"]


def test_navigation_rail_updates_resources(qtbot):
    rail = NavigationRail()
    rail.update_resources(cpu=12, ram_gb=5.2, vram_gb=None, gpu=None)
    assert "12%" in rail.resource_text("cpu")
    assert "N/A" in rail.resource_text("vram")
```

Add explicit-default wrapper coverage in `tests/test_config_page.py`:

```python
from llama_app.ui.widgets.config_page import DefaultFloatField, DefaultIntField


def test_default_int_field_distinguishes_none_and_zero(qtbot):
    field = DefaultIntField(0, 100, "自动")
    qtbot.addWidget(field)
    assert field.config_value() is None
    field.set_config_value(0)
    assert field.config_value() == 0


def test_default_float_field_round_trips_explicit_zero(qtbot):
    field = DefaultFloatField(0.0, 1.0, 0.01, "0.8")
    qtbot.addWidget(field)
    field.set_config_value(0.0)
    assert field.config_value() == 0.0
```

- [ ] **Step 2: Write failing command-bar tests**

```python
from llama_app.core.process import ServerState
from llama_app.ui.widgets.command_bar import CommandBar


def test_command_bar_ready_state(qtbot):
    bar = CommandBar()
    qtbot.addWidget(bar)
    bar.set_server_state(ServerState.READY)
    assert not bar.start_button.isEnabled()
    assert bar.stop_button.isEnabled()
    assert bar.restart_button.isEnabled()
    assert "运行" in bar.status_text()
```

- [ ] **Step 3: Run component tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_navigation_rail.py tests/test_command_bar.py tests/test_config_page.py -v`  
Expected: the three new modules are missing.

- [ ] **Step 4: Implement `NavigationRail`**

Implement a `QFrame` with a `QListWidget` whose items store stable keys in `Qt.UserRole`:

```python
PAGES = (
    ("model", "模型 / 服务端", "选择模型与运行程序"),
    ("performance", "性能", "CPU、GPU 与缓存"),
    ("network", "网络", "地址、端口与访问控制"),
    ("sampling", "采样", "生成行为与随机性"),
    ("advanced", "高级", "多 GPU、LoRA 与诊断"),
    ("monitor", "监控", "资源与速度测试"),
    ("presets", "预设", "保存与管理配置"),
)

class NavigationRail(QFrame):
    page_selected = Signal(str)

    def select_page(self, key: str) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(Qt.UserRole) == key:
                self._list.setCurrentRow(row)
                return
        raise KeyError(key)

    def current_page(self) -> str:
        item = self._list.currentItem()
        return item.data(Qt.UserRole) if item is not None else ""

    def resource_text(self, key: str) -> str:
        if key not in self._resource_labels:
            raise KeyError(key)
        return self._resource_labels[key].text()
```

Resource labels expose `resource_text(key)` for tests and `update_resources(...)` for the window.

- [ ] **Step 5: Implement `CommandBar`**

Expose stable signals and public controls:

```python
class CommandBar(QFrame):
    start_requested = Signal()
    stop_requested = Signal()
    restart_requested = Signal()
    preset_selected = Signal(str)

    def set_server_state(self, state: ServerState) -> None:
        running = state in {ServerState.STARTING, ServerState.LOADING, ServerState.READY}
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.restart_button.setEnabled(running)
        self._status.setText(STATE_LABELS[state])
        self._status.setProperty("state", state.value)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

    def set_dirty(self, dirty: bool) -> None:
        self._dirty.setText("未保存" if dirty else "")

    def status_text(self) -> str:
        return self._status.text()
```

Use `QStyle.StandardPixmap` icons, text labels, tooltips, and accessible names.

- [ ] **Step 6: Implement scroll primitives and theme states**

```python
def make_scroll_page(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(widget)
    return scroll


class SectionTitle(QLabel):
    def __init__(self, title: str, description: str = ""):
        super().__init__(f"<b>{title}</b><br><span>{description}</span>")
        self.setObjectName("sectionTitle")


class DefaultIntField(QWidget):
    changed = Signal()

    def __init__(self, minimum: int, maximum: int, default_label: str):
        super().__init__()
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.use_default = QCheckBox(f"使用 llama 默认值（{default_label}）")
        self.use_default.setChecked(True)
        self.spin.setEnabled(False)
        self.use_default.toggled.connect(self._set_default)
        self.spin.valueChanged.connect(self.changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin, 1)
        layout.addWidget(self.use_default)

    def _set_default(self, checked: bool) -> None:
        self.spin.setEnabled(not checked)
        self.changed.emit()

    def config_value(self) -> int | None:
        return None if self.use_default.isChecked() else self.spin.value()

    def set_config_value(self, value: int | None) -> None:
        self.use_default.setChecked(value is None)
        if value is not None:
            self.spin.setValue(value)


class DefaultFloatField(QWidget):
    changed = Signal()

    def __init__(self, minimum: float, maximum: float, step: float, default_label: str):
        super().__init__()
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.use_default = QCheckBox(f"使用 llama 默认值（{default_label}）")
        self.use_default.setChecked(True)
        self.spin.setEnabled(False)
        self.use_default.toggled.connect(self._set_default)
        self.spin.valueChanged.connect(self.changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin, 1)
        layout.addWidget(self.use_default)

    def _set_default(self, checked: bool) -> None:
        self.spin.setEnabled(not checked)
        self.changed.emit()

    def config_value(self) -> float | None:
        return None if self.use_default.isChecked() else self.spin.value()

    def set_config_value(self, value: float | None) -> None:
        self.use_default.setChecked(value is None)
        if value is not None:
            self.spin.setValue(value)
```

Update QSS for `#navigationRail`, `#commandBar`, selected navigation rows, status properties, visible `:focus`, `:disabled`, and 14 px-equivalent body typography in both themes.

In `__main__.py`, replace the oversized global point size with a DPI-friendly baseline:

```python
    font = QFont()
    font.setPointSizeF(10.5)
    font.setFamilies(["Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI", "sans-serif"])
    app.setFont(font)
```

Remove hard-coded `13pt` declarations from menu/status QSS so all surfaces inherit the same scale.

- [ ] **Step 7: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_navigation_rail.py tests/test_command_bar.py tests/test_config_page.py -v`  
Expected: all shell component tests pass.

- [ ] **Step 8: Commit**

```powershell
git add src/llama_app/__main__.py src/llama_app/ui/widgets/navigation_rail.py src/llama_app/ui/widgets/command_bar.py src/llama_app/ui/widgets/config_page.py src/llama_app/ui/theme.py tests/test_navigation_rail.py tests/test_command_bar.py tests/test_config_page.py
git commit -m "feat: add navigation workbench shell"
```

## Task 7: Log Drawer, Filtering, and Theme Refresh

**Files:**
- Modify: `src/llama_app/ui/widgets/log_panel.py`
- Modify: `tests/test_log_panel.py`

- [ ] **Step 1: Write failing log behavior tests**

```python
def test_log_panel_filters_stderr(qtbot):
    panel = LogPanel()
    panel.append_line("normal", "stdout")
    panel.append_line("problem", "stderr")
    panel.set_filter("stderr")
    assert "normal" not in panel.toPlainText()
    assert "problem" in panel.toPlainText()


def test_log_panel_caps_records_while_filtered(qtbot):
    panel = LogPanel(max_lines=2)
    panel.append_line("one", "stdout")
    panel.append_line("two", "stderr")
    panel.append_line("three", "stdout")
    panel.set_filter("all")
    assert "one" not in panel.toPlainText()
    assert "two" in panel.toPlainText()
    assert "three" in panel.toPlainText()
```

- [ ] **Step 2: Run log tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_log_panel.py -v`  
Expected: `set_filter` does not exist.

- [ ] **Step 3: Implement a record-backed log view**

```python
from collections import deque

        self._records: deque[tuple[str, str]] = deque(maxlen=max_lines)
        self._filter = "all"
        self._auto_scroll = True

    def append_line(self, line: str, stream: str = "stdout") -> None:
        self._records.append((line, stream))
        if self._filter in {"all", stream}:
            self._append_visible(line, stream)

    def set_filter(self, stream: str) -> None:
        if stream not in {"all", "stdout", "stderr"}:
            raise ValueError(stream)
        self._filter = stream
        self._rebuild()

    def refresh_theme(self) -> None:
        self._create_formats_from_palette()
        self._rebuild()
```

Build the header with a title, filter combo, auto-scroll checkbox, copy, and clear actions. Keep existing public `clear()` and `toPlainText()` APIs.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_log_panel.py -v`  
Expected: all log tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/llama_app/ui/widgets/log_panel.py tests/test_log_panel.py
git commit -m "feat: improve log drawer controls"
```

## Task 8: Integrate the Navigation Workbench in `MainWindow`

**Files:**
- Modify: `src/llama_app/ui/main_window.py`
- Modify: `src/llama_app/ui/tabs/model_tab.py`
- Modify: `src/llama_app/ui/tabs/performance_tab.py`
- Modify: `src/llama_app/ui/tabs/network_tab.py`
- Modify: `src/llama_app/ui/tabs/sampling_tab.py`
- Modify: `src/llama_app/ui/tabs/advanced_tab.py`
- Modify: `src/llama_app/ui/tabs/monitor_tab.py`
- Modify: `src/llama_app/ui/tabs/presets_tab.py`
- Create: `tests/test_main_window.py`

- [ ] **Step 1: Write failing window integration tests**

```python
from PySide6.QtWidgets import QStackedWidget
from llama_app.ui.main_window import MainWindow


def test_window_uses_navigation_stack(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.navigation.current_page() == "model"
    assert isinstance(window.page_stack, QStackedWidget)
    window.navigation.select_page("network")
    assert window.current_page_key() == "network"


def test_window_marks_changed_config_dirty(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    window = MainWindow()
    qtbot.addWidget(window)
    assert not window.is_dirty()
    window.tab_net.host.setText("0.0.0.0")
    assert window.is_dirty()


def test_window_constructs_at_minimum_size(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1024, 700)
    window.show()
    assert window.size().width() >= 1024
    assert window.page_stack.currentWidget().isVisible()
```

- [ ] **Step 2: Run window tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main_window.py -v`  
Expected: `navigation`, `page_stack`, and dirty-state APIs are absent.

- [ ] **Step 3: Assemble the central workbench**

Replace `QTabWidget` with:

```python
        self.navigation = NavigationRail()
        self.page_stack = QStackedWidget()
        self._page_keys: list[str] = []
        for key, page in self._pages.items():
            self._page_keys.append(key)
            self.page_stack.addWidget(make_scroll_page(page) if key not in {"monitor", "presets"} else page)

        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.navigation)
        workspace_layout.addWidget(self.page_stack, 1)

        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addWidget(self.command_bar)
        upper_layout.addWidget(workspace, 1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(upper)
        splitter.addWidget(self.log)
        splitter.setSizes([650, 210])
        self.setCentralWidget(splitter)
```

Keep stable `_pages` keys matching `NavigationRail.PAGES`.

- [ ] **Step 4: Wire public lifecycle APIs**

Connect command-bar signals to existing handlers. Replace direct action state changes with `command_bar.set_server_state()`. Replace `_server._proc` access with:

```python
    def _build_launch_spec(self, *, check_port: bool = True) -> LaunchSpec:
        cfg = self.collect_config()
        server = validate_executable(cfg.server_path)
        model = validate_model_file(cfg.model_path)
        if cfg.mmproj_path:
            validate_mmproj_file(cfg.mmproj_path)
        port = cfg.port or 8080
        if check_port and not validate_port_available(cfg.host or "127.0.0.1", port):
            raise ValueError(f"port {port} is already in use")
        args = ConfigBuilder.to_args(cfg)
        return LaunchSpec(
            program=str(server),
            arguments=tuple(args),
            cwd=str(model.parent),
            health_url=f"http://127.0.0.1:{port}/health",
            health_timeout_s=120,
        )

    def _on_restart_clicked(self) -> None:
        try:
            spec = self._build_launch_spec(check_port=False)
        except (ValueError, FileNotFoundError) as exc:
            self._show_validation_error(exc)
            return
        self._server.restart(
            spec.program,
            list(spec.arguments),
            cwd=spec.cwd,
            health_url=spec.health_url,
            health_timeout_s=spec.health_timeout_s,
        )

    def current_page_key(self) -> str:
        return self._page_keys[self.page_stack.currentIndex()]

    def is_dirty(self) -> bool:
        return self._dirty
```

Use `format_display_command()` for log output. Keep actual argv unredacted only inside `ServerProcess.start/restart()`.

- [ ] **Step 5: Add dirty-state and preset safeguards**

```python
    def _mark_dirty(self) -> None:
        if self._applying_config:
            return
        self._dirty = True
        self.command_bar.set_dirty(True)

    def _confirm_discard_changes(self) -> bool:
        if not self._dirty:
            return True
        return QMessageBox.question(
            self,
            "未保存的更改",
            "当前配置尚未保存。要放弃这些更改吗？",
        ) == QMessageBox.Yes
```

Connect every page `changed` signal to `_mark_dirty`. Guard preset changes and reset dirty state after a confirmed load/save. Restore `presets/last_loaded` only when that preset still exists.

- [ ] **Step 6: Remove private monitor access and show recovery notice**

Use `MonitorTab.prompt_text()`, `set_test_pending()`, `show_test_result()`, and `show_test_error()`. If `PresetStore.recovery_notice` is set, show one non-modal status/log warning after window construction.

- [ ] **Step 7: Group pages and expose accessible labels**

For each configuration page:

- Add `SectionTitle` widgets for the groups defined in the design.
- Set `QFormLayout` label alignment consistently.
- Set accessible names on browse, add/remove, password, and lifecycle controls.
- Replace Unicode-symbol button labels with text plus Qt standard icons.
- Preserve every existing `values()` and `set_values()` key.

Replace numeric controls that need explicit-zero semantics with `DefaultIntField` or `DefaultFloatField`. Their value API returns `None` only when “使用 llama 默认值” is checked and returns `0` when the checkbox is clear and the numeric value is zero.

- [ ] **Step 8: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main_window.py tests/test_path_picker.py tests/test_status_indicator.py -v`  
Expected: all integration and widget tests pass.

- [ ] **Step 9: Commit**

```powershell
git add src/llama_app/ui/main_window.py src/llama_app/ui/tabs src/llama_app/ui/widgets tests/test_main_window.py tests/test_path_picker.py tests/test_status_indicator.py
git commit -m "feat: integrate navigation workbench UI"
```

## Task 9: Full Regression, Visual QA, Documentation, and Packaging

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run the full suite**

Run: `.venv\Scripts\python.exe -m pytest -q`  
Expected: all tests pass, with no unhandled Qt exceptions or `pynvml` distribution warning.

- [ ] **Step 2: Compile all source and tests**

Run: `.venv\Scripts\python.exe -m compileall -q src tests`  
Expected: exit code 0 and no output.

- [ ] **Step 3: Capture light and dark screenshots at two sizes**

Render the window through Qt at `1024×700` and `1280×860` for both themes. Save accepted screenshots under `.superpowers/ui-audit/` with these names:

```text
workbench-light-1024x700.png
workbench-light-1280x860.png
workbench-dark-1024x700.png
workbench-dark-1280x860.png
```

Inspect every image. Reject any image with clipping, unreadable text, missing controls, incorrect selected states, or collapsed log controls.

- [ ] **Step 4: Compare against the selected target**

Place the selected reference `docs/superpowers/specs/assets/2026-06-19-navigation-workbench.png` and the `1280×860` implementation screenshot into one side-by-side comparison image. Verify:

- persistent left navigation;
- persistent lifecycle command bar;
- clear page grouping;
- compact resource summary;
- usable log drawer;
- restrained blue-gray hierarchy;
- no card nesting or invented features.

Fix visible mismatches that violate the spec, then recapture and compare once more.

- [ ] **Step 5: Update README**

Document the navigation layout, secret-persistence behavior, supported themes, keyboard shortcuts, and development commands. Include this security note verbatim:

```markdown
API keys and Hugging Face tokens are session-only: they are passed to the active
llama-server process but are redacted from displayed commands and omitted from
saved presets.
```

- [ ] **Step 6: Build the Windows executable**

Run: `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean pyinstaller.spec`  
Expected: exit code 0 and `dist/llama-gui.exe` exists.

- [ ] **Step 7: Smoke-start the packaged executable**

Start `dist/llama-gui.exe` hidden, verify it remains running for four seconds, then terminate the smoke-test process.  
Expected: process stays alive and exits only when the test stops it.

- [ ] **Step 8: Check the final diff**

Run: `git diff --check` and `git status --short`  
Expected: no whitespace errors; only intended source, tests, docs, and dependency metadata are changed.

- [ ] **Step 9: Commit**

```powershell
git add README.md src tests pyproject.toml pyinstaller.spec
git commit -m "docs: finalize workbench release guidance"
```

---

## Final Verification Matrix

| Requirement | Verification |
|---|---|
| Seven areas preserved | `tests/test_main_window.py` navigation assertions |
| Persistent lifecycle controls | `tests/test_command_bar.py` and screenshots |
| Non-blocking stop/restart | `tests/test_process.py` timing and restart tests |
| Unexpected exits remain errors | `tests/test_process.py::test_unexpected_nonzero_exit_is_error` |
| Secrets absent from UI/presets | `tests/test_command.py` and `tests/test_presets.py` |
| Preset recovery | corruption and malformed-structure preset tests |
| Honest speed metrics | parser tests and `count_source` UI label |
| High-DPI/minimum-size usability | 1024×700 screenshots plus Qt smoke test |
| Light/dark state readability | four visual QA screenshots |
| Distribution integrity | full pytest, compileall, PyInstaller, EXE smoke start |
