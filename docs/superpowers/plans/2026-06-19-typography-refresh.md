# Typography Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make llama-gui typography larger, Chinese-first, visually consistent, and readable without changing application behavior.

**Architecture:** Keep typography centralized in the application font and theme QSS. Use object-name selectors for navigation, section titles, command-bar summaries, and the log view so hierarchy remains consistent in both themes.

**Tech Stack:** Python 3.12, PySide6, Qt Style Sheets, pytest-qt, PyInstaller.

---

### Task 1: Define the typography contract

**Files:**
- Modify: `tests/test_command_bar.py`
- Modify: `tests/test_log_panel.py`

- [ ] **Step 1: Write failing tests**

Update the application-font assertion to require 11.5 pt and the Chinese-first family order. Assert the generated QSS contains the 11.5 pt body rule, 12 pt controls, 14 pt section title, taller controls, and navigation typography. Assert the log text edit uses an 11 pt monospace font.

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_command_bar.py tests/test_log_panel.py -q`

Expected: failures showing the current 10.5 pt font, old family order, missing hierarchy rules, and default log font.

### Task 2: Implement the centralized typography system

**Files:**
- Modify: `src/llama_app/__main__.py`
- Modify: `src/llama_app/ui/theme.py`
- Modify: `src/llama_app/ui/widgets/log_panel.py`

- [ ] **Step 1: Set the application font**

Set `QFont` to 11.5 pt with families `Microsoft YaHei UI`, `Segoe UI Variable`, `Segoe UI`, and `sans-serif`.

- [ ] **Step 2: Add QSS hierarchy**

Add explicit body, menu, control, navigation, command-bar, section-title, status, and resource-summary sizes. Raise input minimum height to 28 px, button minimum height to 30 px, and preserve 1024×700 scrolling behavior.

- [ ] **Step 3: Set log typography**

Assign the log text edit an 11 pt `Cascadia Mono`/`Consolas` fallback font without changing record formatting or filtering.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_command_bar.py tests/test_log_panel.py -q`

Expected: all focused tests pass.

### Task 3: Visual and distribution verification

**Files:**
- Build output: `dist/llama-gui.exe`

- [ ] **Step 1: Run the full suite**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Inspect both themes**

Render the same 1280×860 workbench state in light and dark themes. Check typography hierarchy, clipping, navigation line spacing, control heights, and log readability.

- [ ] **Step 3: Build the executable**

Run: `.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean pyinstaller.spec`

Expected: `dist/llama-gui.exe` exists.

- [ ] **Step 4: Smoke-start the executable**

Launch `dist/llama-gui.exe`, verify a targetable `llama-gui` window appears, and record file size and SHA256.

- [ ] **Step 5: Commit**

```powershell
git add src/llama_app/__main__.py src/llama_app/ui/theme.py src/llama_app/ui/widgets/log_panel.py tests/test_command_bar.py tests/test_log_panel.py docs/superpowers/plans/2026-06-19-typography-refresh.md
git commit -m "style: improve application typography"
```
