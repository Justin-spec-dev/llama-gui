# llama-gui UI Workbench Optimization Design

**Date:** 2026-06-19  
**Status:** Approved direction; pending written-spec review  
**Visual target:** [Navigation Workbench](assets/2026-06-19-navigation-workbench.png)

## 1. Goal

Modernize llama-gui into a clearer Windows desktop workbench without changing its configuration semantics or removing existing capabilities. The work also fixes high-risk lifecycle, security, persistence, and measurement defects found during the project review.

The selected direction is a medium redesign: preserve the seven functional areas and the PySide6 desktop architecture, while replacing the top-tab-first experience with persistent navigation and server controls.

## 2. Scope

### In scope

- Replace the top tab bar with a left navigation rail backed by a `QStackedWidget`.
- Add a persistent command bar for preset selection, model summary, server state, start, stop, and restart.
- Reorganize configuration pages into readable sections with scrolling, inline defaults, and validation feedback.
- Make the log panel collapsible and improve filtering, copy, clear, auto-scroll, and stream readability.
- Keep live resource summaries visible and retain full plots on the monitoring page.
- Preserve light, dark, and system themes, keyboard shortcuts, presets, speed testing, and packaging.
- Fix the P0/P1 logic issues listed in section 8.
- Add tests for lifecycle behavior, secret redaction, preset recovery, speed-test parsing, navigation, and configuration round trips.

### Out of scope

- Bundling or downloading `llama-server.exe` automatically.
- Multi-server management.
- A built-in chat client.
- Cross-platform packaging.
- Windows Credential Manager integration; secrets remain session-only instead.
- Broad replacement of PySide6 or the existing `Config` model.

## 3. Information Architecture

The seven existing areas remain intact:

1. Model / Server
2. Performance
3. Network
4. Sampling
5. Advanced
6. Monitoring
7. Presets

The main window is divided into four persistent regions:

- **Left navigation:** section name, short description, selected state, and compact CPU/RAM/VRAM/GPU summary.
- **Top command bar:** current preset, selected model, lifecycle status, start, stop, and restart.
- **Content workspace:** one active configuration or monitoring page.
- **Bottom log drawer:** collapsible, resizable, and shared across every page.

The status bar remains a compact fallback for readiness and runtime metadata rather than duplicating the entire resource display.

## 4. Visual System

- Retain the existing blue-gray identity, with restrained surfaces and no gradients or glass effects.
- Use 14 px-equivalent body text and a small, consistent heading scale instead of a global 13 pt font.
- Use spacing and alignment before borders; use shadows only when required for a floating surface.
- Use clear focus rings and text labels so state is never conveyed by color alone.
- Use native or Qt standard icons. Unicode glyphs are not used as toolbar icons because font availability is inconsistent.
- Support 100%, 125%, and 150% Windows scaling and a minimum usable window size of 1024×700.
- Long forms live inside `QScrollArea`; controls must not clip at the minimum size.

## 5. UI Components

### `NavigationRail`

Owns section selection only. It emits a page key and has no configuration or server knowledge. Each entry has a title and one-line purpose. Selection is keyboard reachable.

### `CommandBar`

Shows the selected preset and a shortened model path, plus a text-and-color server state. It owns no lifecycle logic; start, stop, and restart are signals handled by the window/controller.

### Configuration pages

Existing tab classes remain the source of configuration values but are presented as pages. Each page uses focused groups and contextual help:

- Model: executable, model, and optional multimodal projector.
- Performance: common controls first; memory/cache controls second.
- Network: bind settings, access control, and optional endpoints.
- Sampling: core sampling controls first; penalties and reasoning second.
- Advanced: multi-GPU, LoRA, Hugging Face, and diagnostics.

Default/unset values remain semantically distinct from explicit values. Zero-capable fields receive an explicit “Use llama default” state instead of relying on a hidden `specialValueText` transition.

### `LogPanel`

Adds stream/level filtering, auto-scroll, copy, and clear controls. It preserves the 5,000-line cap. Command lines are rendered through a redactor that masks API keys and Hugging Face tokens.

### Monitoring

The navigation rail shows current totals. The monitoring page keeps 60-second plots and the speed-test form. Results distinguish server-reported token counts from fallback streamed-content counts.

## 6. Architecture and Boundaries

`MainWindow` remains the composition root but loses reusable UI and lifecycle details.

- `ui/main_window.py`: window assembly, high-level signal wiring, and persistence hooks.
- `ui/widgets/navigation_rail.py`: navigation and compact resource summary.
- `ui/widgets/command_bar.py`: preset/model/status/lifecycle controls.
- `ui/widgets/config_page.py`: scrollable page and section primitives.
- `ui/widgets/log_panel.py`: log presentation and filtering.
- `core/command.py`: command display formatting and secret redaction.
- `core/process.py`: asynchronous lifecycle, restart, health checks, and exit classification.
- Existing `Config`, `PresetStore`, `ResourceMonitor`, and `SpeedTester` retain their focused roles.

UI widgets communicate with the composition root through signals. UI code must not access private members such as `ServerProcess._proc` or `MonitorTab._prompt`.

## 7. Data Flow

### Start

1. Pages provide raw values.
2. `Config` validates enums and cross-field constraints.
3. Path and port validation produces field-specific messages.
4. `ConfigBuilder` produces argv.
5. The redactor produces a safe display command for logs/preview.
6. `ServerProcess.start()` transitions `STOPPED → STARTING → LOADING`.
7. A non-blocking health probe transitions to `READY` or `ERROR`.
8. Resource monitoring starts after a valid PID exists.

### Stop and restart

- Stop calls `terminate()` and returns immediately. A single-shot timer escalates to `kill()` after the grace period.
- `ServerProcess` records whether exit was user-requested.
- User-requested exit becomes `STOPPED`; unexpected/non-zero exit becomes `ERROR`.
- Restart stores a complete launch specification before stopping, then starts exactly once after the prior process finishes.

### Presets

- Preset selection warns before discarding dirty edits.
- Presets store configuration values but omit `api_key` and `hf_token`.
- Corrupt or structurally invalid JSON is backed up and replaced with an empty store; the UI shows a non-fatal recovery notice.
- Existing preset files remain readable.

## 8. Review Findings and Required Fixes

### P0 — security

1. **Secrets are printed into logs.** The displayed command includes `--api-key` and `--hf-token`. Mask both values everywhere outside the actual `QProcess` argument list.
2. **Secrets are persisted in plaintext presets.** Do not save API or Hugging Face tokens. Environment variables or session entry remain supported.

### P1 — lifecycle and correctness

1. **Restart is race-prone.** The current implementation waits for the process to finish before connecting the restart callback, so the signal can already be lost.
2. **Stop blocks the GUI thread.** `waitForFinished(5000)` can freeze the interface for five seconds, followed by another two-second wait after kill.
3. **Unexpected exits are reported as stopped.** `_on_finished()` always sets `STOPPED`, overriding failure context.
4. **Health polling blocks the GUI thread.** `urllib.request.urlopen(..., timeout=1)` runs from the main-thread timer.
5. **Corrupt presets can prevent application startup.** `PresetStore` raises during `MainWindow` construction instead of recovering.
6. **Speed-test token counts are not token counts.** The code counts SSE data chunks, including chunks that may not contain generated text.

### P2 — UX, accuracy, and maintainability

1. `MainWindow` reaches into private members of `ServerProcess` and `MonitorTab`.
2. The monitor creates a new `psutil.Process` every sample, making process CPU sampling unreliable; cache the process object per PID.
3. GPU monitoring always uses device 0 and does not reflect a selected main GPU or multi-GPU configuration.
4. Switching presets can silently discard edits; the existing `changed` signals are not used for dirty tracking.
5. The saved “last loaded preset” is never restored.
6. Theme changes do not rebuild cached log colors.
7. Long pages are not scrollable and can clip on smaller displays or high DPI.
8. Icon-only Unicode controls are font-dependent and have weak accessible labeling.
9. Configuration validation is mostly deferred to modal dialogs; cross-field issues such as `ubatch_size > batch_size` need inline feedback.
10. The application has only 40 tests and limited coverage of main-window flows, page round trips, restart, failure states, and theme behavior.
11. `pynvml` packaging emits a deprecation warning; migrate the distribution dependency to `nvidia-ml-py` while retaining the `pynvml` import API.

## 9. Error Handling

- Validation errors are shown next to the relevant field and summarized in a single non-destructive banner.
- Process start failures and unexpected exits keep the last error visible until the next start attempt.
- Health timeout includes elapsed time and the checked endpoint.
- Preset recovery never destroys the backup and never blocks startup.
- Speed-test failures restore the button state and distinguish timeout, authorization, connection, protocol, and server-response errors.
- Closing while stopping remains responsive; shutdown completion is coordinated asynchronously.

## 10. Testing Strategy

### Core tests

- argv generation and cross-field validation.
- secret redaction in display commands.
- preset round trip, migration, secret omission, malformed structure, and corruption recovery.
- process state transitions for start, requested stop, forced kill, unexpected exit, timeout, and restart.
- speed-test SSE parsing, usage-based count, fallback count, empty stream, and malformed events.
- resource-monitor PID caching and unavailable GPU behavior.

### UI tests

- navigation switches the correct page and remains keyboard accessible.
- command bar reflects every server state and enables the correct actions.
- every page round-trips explicit, unset, and explicit-zero values.
- dirty state and preset-switch confirmation.
- log filtering, redaction, line cap, and theme refresh.
- minimum-size and light/dark smoke tests.

### Release checks

- full pytest suite.
- source compilation.
- offscreen window construction at 1024×700 and 1280×860.
- visual comparison against the selected Navigation Workbench target in light and dark modes.
- PyInstaller single-file build and packaged executable smoke start.

## 11. Acceptance Criteria

1. All existing llama-server parameters and preset operations remain available.
2. The seven areas are reachable from a persistent left navigation rail.
3. Lifecycle controls and status remain visible on every page.
4. Stop and health polling never block the UI thread.
5. Restart occurs exactly once and unexpected exits remain `ERROR`.
6. Logs and presets never expose API or Hugging Face token values.
7. Corrupt presets recover without blocking startup.
8. Long pages are usable at 1024×700 and 150% scaling.
9. Light and dark themes have readable focus, hover, disabled, selected, error, and success states.
10. The full automated suite, packaging build, and packaged smoke test pass.

## 12. Follow-up Recommendations

These are intentionally deferred unless later prioritized:

- Windows Credential Manager integration for optional secure secret persistence.
- Per-GPU selection and aggregate multi-GPU charts.
- llama-server capability detection to hide unsupported flags by version.
- Import/export of sanitized presets.
- Structured log parsing and searchable diagnostics bundles.
- Type checking, linting, coverage thresholds, dependency locking, and CI release builds.
