# llama-gui

Windows 桌面应用，图形化管理 [llama.cpp](https://github.com/ggerganov/llama.cpp) 的 `llama-server`，告别手敲命令行。

## 功能

- **可视化配置** — 所有 `llama-server` 参数通过表单配置，参数旁有 `?` 悬停提示解释含义
- **预设管理** — 保存/加载/删除多套配置预设，一键切换不同模型
- **进程控制** — 启动/停止/重启 llama-server，实时查看输出日志，状态灯显示运行状态
- **资源监控** — CPU、内存、显存、GPU 占用率实时图表
- **速度测试** — 一键测试 tok/s 速率和首 token 延迟
- **浅色/深色主题** — 靛蓝配色，菜单切换

## 下载

从 [Releases](https://github.com/Justin-spec-dev/llama-gui/releases) 下载 `llama-gui.exe`。

## 使用

1. 下载 `llama-server.exe`（从 [llama.cpp Releases](https://github.com/ggerganov/llama.cpp/releases)）
2. 启动 `llama-gui.exe`
3. **模型** 标签页：点击 `…` 选择 `llama-server.exe` 和 `.gguf` 模型文件
4. 在其它标签页调整参数（不填 = 使用 llama 默认值）
5. 点击 **▶ 启动**
6. 在 **监控** 标签页查看资源占用和测速
7. `Ctrl+S` 保存当前配置为预设

## 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+Enter` | 启动服务器 |
| `Ctrl+.` | 停止服务器 |
| `F5` | 重启服务器 |
| `Ctrl+S` | 保存当前为预设 |
| `Ctrl+L` | 清空日志 |
| `Ctrl+Q` | 退出 |
| `F1` | 帮助 |

## 开发

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"

# 运行
python -m llama_app

# 测试
pytest tests/ -v
```

## 打包

```bash
pip install pyinstaller pillow
pyinstaller pyinstaller.spec
# → dist/llama-gui.exe
```

## 项目结构

```
src/llama_app/
├── core/                  # 纯业务逻辑
│   ├── command.py         #   命令脱敏与格式化
│   ├── config.py          #   配置数据模型与 CLI 参数构建
│   ├── validators.py      #   路径/端口校验
│   ├── presets.py         #   预设持久化（JSON + 原子写入）
│   ├── process.py         #   QProcess 异步生命周期 + 健康检查
│   ├── monitor.py         #   CPU/RAM/VRAM/GPU 定时采样
│   └── speedtest.py       #   HTTP 流式测速（QThreadPool）
├── ui/                    # PySide6 界面
│   ├── main_window.py     #   主窗口组合根
│   ├── theme.py           #   主题引擎（light/dark/auto + QSS）
│   ├── tabs/              #   7 个标签页
│   │   ├── model_tab.py
│   │   ├── performance_tab.py
│   │   ├── network_tab.py
│   │   ├── sampling_tab.py
│   │   ├── advanced_tab.py
│   │   ├── monitor_tab.py
│   │   └── presets_tab.py
│   └── widgets/           # 通用控件
│       ├── command_bar.py     #   顶部控制栏（预设/状态/启停）
│       ├── navigation_rail.py #   左侧持久导航 + 资源概览
│       ├── config_page.py     #   可滚动配置页 + SectionTitle
│       ├── resource_plot.py   #   pyqtgraph 实时时序图
│       ├── log_panel.py       #   日志面板（stdout/stderr 着色）
│       ├── path_picker.py     #   文件路径选择器
│       └── status_indicator.py
└── resources/             # 图标资源
    ├── icon.png
    ├── icon.ico
    ├── spin_up_light.png
    ├── spin_down_light.png
    ├── spin_up_dark.png
    └── spin_down_dark.png
```

## License

MIT
