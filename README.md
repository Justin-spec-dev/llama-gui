# llama-gui

A Windows GUI launcher for [`llama-server`](https://github.com/ggerganov/llama.cpp)
that lets you configure parameters, manage presets, and watch resource usage —
no more hand-typing command-line flags.

## Features

- Form-based configuration of 30+ `llama-server` flags
- Save / load / rename / delete named presets
- Live process control: start, stop, restart, with health-check polling
- Real-time CPU / RAM / VRAM / GPU% monitoring (NVIDIA via pynvml)
- Built-in tok/s speed test
- Light / dark / auto theme
- Keyboard shortcuts (Ctrl+S to save preset, F5 to restart, etc.)

## Requirements

- Windows 10 / 11
- Python 3.10+ (only if running from source)
- A `llama-server.exe` from the
  [llama.cpp releases page](https://github.com/ggerganov/llama.cpp/releases)

## Running from source

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m llama_app
```

## Building a single-file `.exe`

```bash
pip install pyinstaller
pyinstaller pyinstaller.spec
# → dist/llama-gui.exe
```

## Quick start

1. Launch llama-gui.
2. On the **Model** tab, click `…` next to `llama-server.exe` and pick your
   `llama-server.exe`. Do the same for the model file.
3. Adjust parameters on the other tabs as needed.
4. Click **▶ 启动** (or press `Ctrl+Enter`).
5. Watch the log panel and the **监控** tab for resource usage.
6. When you're done, click **■ 停止** (or `Ctrl+.`).

To save your configuration for later, press `Ctrl+S` and give the preset a name.

## Project layout

See `docs/superpowers/specs/2026-06-14-llama-gui-design.md` for the full
design and `docs/superpowers/plans/2026-06-14-llama-gui.md` for the
implementation plan.

## License

Personal project — license to be determined.
