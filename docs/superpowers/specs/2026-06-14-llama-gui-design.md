# llama-gui 设计文档

**日期**：2026-06-14（初稿）/ 2026-06-19（更新至 v1.0）
**状态**：已实现（v1.0）
**仓库**：https://github.com/Justin-spec-dev/llama-gui

## 1. 概述

Windows 桌面 GUI 工具，用于图形化管理 [llama.cpp](https://github.com/ggerganov/llama.cpp) 的 `llama-server`，替代手敲命令行。可配置参数、管理预设、启停服务、监控资源、测试速度。

### 目标
- 用表单式界面替代命令行（`llama-server.exe -m ... -c ...`）。
- 通过命名预设快速切换不同模型配置。
- 展示 tok/s、CPU、内存、显存、GPU 利用率，方便参数调优。
- 单人使用，单台 Windows 机器。

### 不做的事
- 多实例管理（同一时间只跑一个 llama-server）。
- 内置聊天界面（v1 不做）。
- 捆绑 `llama-server.exe`（用户自己提供）。
- 跨平台（仅 Windows；PySide6 代码本身可移植）。

## 2. 技术栈

| 层 | 选择 | 说明 |
|---|---|---|
| 语言 | Python 3.10+ | 需要 PEP 604 联合类型语法（`int \| None`） |
| 界面 | PySide6（Qt 6.5+） | 原生外观，控件丰富 |
| 主题 | 自定义 QSS | 无外部主题库，内置浅色/深色双方案 |
| 图表 | `pyqtgraph` 0.13+ | 实时滚动折线图，比 matplotlib 轻 10 倍 |
| 系统监控 | `psutil` 5.9+ + `pynvml` 11.5+ | CPU/内存用 psutil；显存/GPU% 用 pynvml（NVIDIA） |
| HTTP 客户端 | `httpx` 0.27+ | 流式 SSE 解析，用于测速 |
| 持久化 | `QSettings` + JSON | 窗口位置/主题/路径 → QSettings；预设 → `%APPDATA%\llama-gui\presets.json` |
| 打包 | PyInstaller | 单文件 `.exe`，含自定义图标 |
| 测试 | `pytest` + `pytest-qt` | 40 个用例，`core/` 层零 PySide6 依赖 |

## 3. 架构

```
┌──────────────── llama-gui（PySide6 GUI）──────────────────┐
│                                                            │
│  主窗口（MainWindow）                                        │
│   ├── 菜单栏          文件 / 视图（主题切换） / 帮助（快捷键）   │
│   ├── 工具栏          ▶启动 ■停止 ↻重启 ●状态灯 预设▼        │
│   ├── 标签页（7 个）                                         │
│   │    ├── 模型         服务端程序 / 模型文件 / 投影器          │
│   │    ├── 性能         显卡层数 / 上下文 / 线程 / 批大小等      │
│   │    ├── 网络         监听地址 / 端口 / API密钥 / Web界面等   │
│   │    ├── 采样         温度 / Top-K / Top-P / 种子 / 推理等   │
│   │    ├── 高级         多GPU / LoRA / HF下载 / 日志级别等     │
│   │    ├── 监控         速度测试 + CPU/RAM/VRAM/GPU 折线图     │
│   │    └── 预设         保存 / 加载 / 重命名 / 删除            │
│   ├── 日志面板（底部）   实时输出 stdout/stderr 分色显示         │
│   └── 状态栏           CPU、RAM、VRAM、GPU 实时数值            │
│                                                            │
│  业务逻辑层（无 PySide6 依赖，可独立测试）                       │
│   ├── Config dataclass   40+ 参数字段，None = 不传参           │
│   ├── ConfigBuilder      Config → list[str] 命令行参数         │
│   ├── PresetStore        JSON 原子写入，损坏时备份              │
│   ├── ServerProcess      QProcess 包装 + 状态机 + 健康检查      │
│   ├── ResourceMonitor    QTimer 1Hz，psutil + pynvml          │
│   └── SpeedTester        QRunnable，httpx 流式请求             │
│                                                            │
│  持久化                                                      │
│   ├── presets.json         %APPDATA%\llama-gui\              │
│   └── QSettings（注册表）  窗口大小、主题、最近路径              │
└────────────────────────────────────────────────────────────┘
```

### 设计原则
- **`core/` 层零 PySide6 导入** — 纯逻辑，可用普通 pytest 直接测试。
- **空值 = 不传参数** — 构造器遇到 `None` 就跳过该 flag，让 llama-server 用自身默认值。
- **勾选框语义对齐官方默认**：默认开启的参数标签为"禁用 XXX"（勾选 = 传 `--no-xxx`），默认关闭的参数标签为"启用 XXX"（勾选 = 传 `--xxx`）。

## 4. 关键设计决策

### 4.1 "不填不传"约定

每个控件初始处于"未设置"状态。只有用户明确改过的参数才会出现在命令行中。

| 控件类型 | 未设置状态 | `values()` 返回 |
|---|---|---|
| 整数输入框 | 值为 `0`，显示 `"(默认 NNN)"` | 若用户未改过 → `None`；改过 → 实际值 |
| 浮点输入框 | 值为 `0.0`，显示 `"(默认 N.N)"` | 同上 |
| 下拉框 | 第一项为 `"(默认 XXX)"` | 若当前项以 `"(默认"` 开头 → `None`；否则 → 实际值 |
| "启用型"勾选框 | 不勾选 | 勾选 → `True`，不勾 → `None` |
| "禁用型"勾选框 | 不勾选 | 勾选 → `False`（传 `--no-xxx`），不勾 → `None` |
| 文本输入框 | 空字符串 | `text or None` |

用户修改值时，`specialValueText` 被清空，`values()` 开始返回实际数值。

### 4.2 勾选框标签约定

| llama 默认 | 勾选框标签格式 | 勾选时传参 |
|---|---|---|
| **开启** | "禁用 XXX（llama 默认: 启用）" | `--no-xxx`（即 `False`） |
| **关闭** | "启用 XXX（llama 默认: 关闭）" | `--xxx`（即 `True`） |

应用此约定的参数：`cont_batching`、`enable_ui`、`jinja`、`cache_prompt`（禁用型）；`mlock`、`metrics`、`verbose`（启用型）。

### 4.3 `0.0.0.0` 问题

`0.0.0.0` 是绑定地址（监听所有网卡），不能作为连接地址使用。受影响的三处均已修复：

| 组件 | 修复方式 |
|---|---|
| 健康检查（`/health` 轮询） | 固定使用 `http://127.0.0.1:{port}/health` |
| 速度测试（连接服务器） | 固定使用 `http://127.0.0.1:{port}/v1/chat/completions` |
| 端口占用检测 | 使用 `cfg.host or "127.0.0.1"`，127.0.0.1 始终可绑定 |

### 4.4 资源监控启动时机

在服务器进入 **LOADING** 状态时即启动（不等到 READY），以便在进程启动后立即看到基线资源占用。

## 5. 模块详情

### 5.1 `core/config.py`
- `Config`：dataclass，40+ 字段，类型为 `X | None`（未设）或 `bool`（显式开/关）。
- `ConfigBuilder.to_args(cfg)`：将 Config 转换为 `list[str]` 命令行参数。
  - `None` 字段 → 跳过。
  - `True` → 发射 flag（如 `--mlock`）。
  - 取反字段（`no_mmap`）的 `True` → 发射 `--no-*`。
  - 三态字段（`enable_ui` 等）：`True` → 正向 flag，`False` → 反向 flag，`None` → 跳过。
  - 字符串枚举在发射前校验（无效值抛出 `ValueError`）。
- `enable_ui` 为三态（`None`=默认, `True`=`--ui`, `False`=`--no-ui`）。
- `jinja`、`cont_batching`、`cache_prompt` 同为三态。

### 5.2 `core/presets.py`
- `PresetStore`：JSON 文件，路径 `%APPDATA%\llama-gui\presets.json`。
- 原子写入：先写临时文件，再 `os.replace()` 重命名。
- 文件损坏时：重命名为 `.bak`，重建空存储。
- 方法：`list()`、`get(name)`、`save(preset)`、`delete(name)`、`rename(old, new)`。

### 5.3 `core/process.py`
- `ServerProcess(QObject)`：封装 `QProcess`。
- 状态机：`STOPPED → STARTING → LOADING → READY → (STOPPED | ERROR)`。
- 健康检查：500ms 间隔轮询 `/health`，120s 超时。
- `stop()`：先 `terminate()`，等 5s，不行再 `kill()`。
- 日志行前缀 `[stderr]` 用于后续颜色区分。

### 5.4 `core/monitor.py`
- `ResourceMonitor(QObject)`：QTimer 1 秒采集一次。
- `psutil`：CPU 总体%、进程 CPU%、系统内存、进程 RSS。
- `pynvml`：GPU 利用率%、显存占用。无 NVIDIA 时优雅降级为 `None`（界面显示 "N/A"）。
- `process_gone` 信号：PID 退出时触发 → 主窗口状态切为 ERROR。

### 5.5 `core/speedtest.py`
- `SpeedTester(QObject)`：使用 `QRunnable` + `QThreadPool`（不阻塞 UI）。
- 连接 `http://127.0.0.1:{port}/v1/chat/completions`，`stream: true`。
- 返回：`{tokens, elapsed_s, first_token_ms, tokens_per_sec}`。
- 前置检查：服务器必须处于 READY 状态；否则弹出警告。

## 6. 主题系统

自定义双主题 QSS，无外部主题库依赖。

| 元素 | 浅色 | 深色 |
|---|---|---|
| 背景 | `#f5f5f5` | `#1c1c28` |
| 表面 | `#ffffff` | `#222233` |
| 强调色 | `#3a7abf` | `#4a8abc` |
| 文字 | `#333` | `#c8c8d0` |
| 标签页选中 | `#dce8f0` | `#1c2c3c` |

- `_BASE_QSS`：共享的结构样式（内边距、圆角、字体族等）。
- `_DARK_QSS` / `_LIGHT_QSS`：仅颜色覆盖。
- 变量替换（`$border`、`$accent`、`$press`、`$selectedText`）避免重复代码。
- 全局字体：13pt，Segoe UI / Microsoft YaHei，通过 `QApplication.setFont()` 设置。
- 菜单路径：视图 → 主题 → 浅色 / 深色 / 跟随系统。
- "跟随系统"在 Windows 上通过 `winreg` 读取系统设置。

## 7. 各标签页详情

### 7.1 模型
| 字段 | 控件 | 校验 |
|---|---|---|
| llama-server.exe | 路径选择器（筛选 `*.exe`） | 必填，必须存在 |
| 模型 | 路径选择器（筛选 `*.gguf`） | 必填，必须存在 |
| mmproj | 路径选择器 | 选填，如填了必须存在 |

### 7.2 性能
| 参数 | 控件 | 未设置时显示 |
|---|---|---|
| `-ngl` | 整数框 0–999 | `(默认 auto)` |
| `-ncmoe` | 整数框 0–999 | `(默认 0)` |
| `-c` | 整数框 0–1048576 | `(默认 读模型)` |
| `-t` | 整数框 0–256 | `(默认 自动)` |
| `-tb` | 整数框 0–256 | `(默认 同 -t)` |
| `-b` | 整数框 0–4096 | `(默认 2048)` |
| `-ub` | 整数框 0–4096 | `(默认 512)` |
| `-ctk` | 下拉框 | `(默认 f16)` |
| `-ctv` | 下拉框 | `(默认 f16)` |
| `-fa` | 下拉框 | `(默认 auto)` |
| `--mlock` | 勾选框（启用） | 不勾（默认关闭） |
| `--no-mmap` | 勾选框（禁用） | 不勾（默认启用 mmap） |
| `-np` | 整数框 0–64 | `(默认 自动)` |
| `--cont-batching` | 勾选框（禁用） | 不勾（默认启用） |

### 7.3 网络
| 参数 | 控件 | 未设置时显示 |
|---|---|---|
| `--host` | 文本输入框 | 占位文字：`127.0.0.1 (llama 默认)` |
| `--port` | 整数框 0–65535 | `(默认 8080)` |
| `--api-key` | 文本输入框（密码模式） | 空 |
| `--ui` | 勾选框（禁用） | 不勾（默认启用） |
| `--metrics` | 勾选框（启用） | 不勾（默认关闭） |
| `-a` | 文本输入框 | 空 |
| `--jinja` | 勾选框（禁用） | 不勾（默认启用） |

### 7.4 采样
| 参数 | 控件 | 未设置时显示 |
|---|---|---|
| `-n` | 整数框 | `(默认 无限)` |
| `--temp` | 浮点框 | `(默认 0.8)` |
| `--top-k` | 整数框 | `(默认 40)` |
| `--top-p` | 浮点框 | `(默认 0.95)` |
| `--min-p` | 浮点框 | `(默认 0.05)` |
| `--repeat-penalty` | 浮点框 | `(默认 1.0)` |
| `--repeat-last-n` | 整数框 | `(默认 64)` |
| `--presence-penalty` | 浮点框 | `(默认 0.0)` |
| `--frequency-penalty` | 浮点框 | `(默认 0.0)` |
| `-s` | 整数框 | `(默认 随机)` |
| `--reasoning` | 下拉框 | `(默认 auto)` |
| `--reasoning-budget` | 整数框 | `(默认 无限)` |

### 7.5 高级
| 参数 | 控件 | 未设置时显示 |
|---|---|---|
| `-sm` | 下拉框 | `(默认)` |
| `-ts` | 文本输入框 | 空 |
| `-mg` | 整数框 | `(默认)` |
| `--lora` | 列表 + 添加/移除按钮 | 空 |
| `--hf-repo` | 文本输入框 | 空 |
| `--hf-file` | 文本输入框 | 空 |
| `--hf-token` | 文本输入框（密码） | 空 |
| `-to` | 整数框 | `(默认 3600s)` |
| `-v` | 勾选框（启用） | 不勾（默认关闭） |
| `-lv` | 整数框 0–5 | `(默认 3)` |
| `--no-warmup` | 勾选框（禁用） | 不勾（默认开启预热） |
| `--cache-prompt` | 勾选框（禁用） | 不勾（默认启用） |

### 7.6 监控
- 速度测试：prompt 文本框、开始按钮、结果显示（token 数、耗时、首 token 延迟、tok/s）。
- 4 个 `pyqtgraph` 滚动折线图（60 点窗口，1Hz）：CPU%、RAM GB、VRAM GB、GPU%。
- 图表以 2×2 网格排列，每个下方有当前值标签。
- 速度测试前置检查：服务器必须为 READY 状态，否则弹警告。

### 7.7 预设
- `QListWidget` 列出所有预设名称。
- 双击或点"加载" → 将保存的配置填入各标签页。
- "保存当前为预设…" → 弹窗命名 → `PresetStore.save()`。
- "重命名…" / "删除" 按钮。
- 右侧只读摘要显示：服务端路径、模型路径、ngl、ctx、threads。

## 8. 参数提示（Tooltip）

每个控件都通过 `setToolTip()` 设置了中文说明，内容基于 [llama.cpp 官方文档](https://github.com/ggerganov/llama.cpp/blob/master/tools/server/README.md)。每条提示包含：参数含义、llama 默认值、相关注意事项。

## 9. 日志面板

- `QTextEdit`，只读，等宽字体。
- stdout → 调色板文字颜色；stderr → 红色（深色主题 `#ff6666`，浅色主题 `#cc0000`）。
- `[CMD]` 标记 → 回显实际执行的命令行。
- `[stderr]` 前缀 → 通过 `startswith` 判断（不用 `in`，避免误判）。
- 最多 5000 行，超出从顶部裁剪。
- 工具栏按钮：清空 / 复制选中。

## 10. 快捷键

| 按键 | 操作 | 条件 |
|---|---|---|
| `Ctrl+S` | 保存当前为预设 | 随时 |
| `Ctrl+Enter` | 启动 | 未运行 + 必填项有效 |
| `F5` | 重启 | 运行中 |
| `Ctrl+.` | 停止 | 运行中 |
| `Ctrl+L` | 清空日志 | 随时 |
| `Ctrl+Q` | 退出 | 随时 |
| `F1` | 快捷键帮助 | 随时 |

## 11. 核心流程

### 11.1 启动
1. 用户点击 ▶ 或按 `Ctrl+Enter`。
2. 校验：服务端程序存在、模型文件存在、mmproj（如填了）存在。
3. 端口检测：`socket.bind()` 测试；若被占用，弹确认框。
4. `ConfigBuilder.to_args()` 生成参数列表。
5. 日志面板中回显 `[CMD]` 实际命令。
6. `ServerProcess.start()` 带健康检查 URL `http://127.0.0.1:{port}/health`。
7. 状态流转：STARTING → LOADING → READY（`/health` 返回 200）/ ERROR（120s 超时）。
8. 进入 LOADING 时启动 `ResourceMonitor`。

### 11.2 停止
1. 用户点击 ■ 或按 `Ctrl+.`。
2. `terminate()` → 等 5 秒 → `kill()`。
3. `ResourceMonitor.stop()`。

### 11.3 重启（`F5`）
停止 → 用 `SingleShotConnection` 连接 `_on_start_clicked`（不泄漏信号）。

### 11.4 保存预设（`Ctrl+S`）
1. 弹出命名框。
2. 收集所有标签页的当前配置。
3. `PresetStore.save(Preset.now(name, config))`。
4. 刷新下拉列表，选中刚保存的预设。

### 11.5 速度测试
1. 检查服务器为 READY；否则弹警告。
2. `SpeedTester.run("127.0.0.1", port, api_key, prompt)` 在线程池中运行。
3. 渲染结果或错误信息。

## 12. 错误处理

| 场景 | 处理方式 |
|---|---|
| 启动时服务端程序不存在 | 弹窗，阻止启动 |
| 模型文件不存在 | 弹窗，阻止启动 |
| 端口被占用 | 弹确认框 |
| `presets.json` 损坏 | 备份为 `.bak`，重建空文件 |
| pynvml 不可用 | GPU/VRAM 显示 "N/A"，不报错 |
| 健康检查超时（120s） | 状态切 ERROR，停止服务 |
| 进程意外退出 | `process_gone` 信号 → 状态切 ERROR |
| 速度测试时服务未就绪 | 弹警告，不崩溃 |

## 13. 项目结构

```
llama_app/
├── pyproject.toml
├── pyinstaller.spec
├── README.md
├── .gitignore
├── docs/superpowers/
│   ├── specs/2026-06-14-llama-gui-design.md    ← 本设计文档
│   └── plans/2026-06-14-llama-gui.md           ← 实施计划
├── src/llama_app/
│   ├── __init__.py
│   ├── __main__.py               ← 程序入口
│   ├── core/                     ← 纯业务逻辑（零 PySide6 依赖）
│   │   ├── config.py             Config + ConfigBuilder
│   │   ├── validators.py         路径/端口校验
│   │   ├── presets.py            JSON 预设存储
│   │   ├── process.py            QProcess 进程管理
│   │   ├── monitor.py            资源监控
│   │   └── speedtest.py          速度测试
│   ├── ui/                       ← PySide6 界面
│   │   ├── main_window.py        主窗口
│   │   ├── theme.py              浅色/深色主题
│   │   ├── tabs/                 7 个标签页
│   │   └── widgets/              通用控件
│   └── resources/                图标
│       ├── icon.png              窗口图标
│       └── icon.ico              .exe 文件图标
└── tests/                        ← 40 个测试用例
    ├── conftest.py
    ├── test_config.py            （8）
    ├── test_validators.py        （7）
    ├── test_presets.py           （7）
    ├── test_process.py           （4）
    ├── test_monitor.py           （4）
    ├── test_speedtest.py         （2）
    ├── test_path_picker.py       （3）
    ├── test_log_panel.py         （3）
    └── test_status_indicator.py  （2）
```

共 23 个源文件 + 9 个测试文件 = 32 个 Python 文件。40 个测试用例全部通过。

## 14. 打包

```bash
pip install pyinstaller pillow
pyinstaller pyinstaller.spec
# → dist/llama-gui.exe（单文件，约 90 MB）
```

- 隐藏导入：`psutil`、`pynvml`、`httpx`、`pyqtgraph`（已写入 `.spec`）。
- 图标：`icon.ico`（多分辨率 16–256px，用 PIL 生成）。
- **不**捆绑 `llama-server.exe`（用户通过界面指定路径）。

## 15. 开发过程中修复的 Bug

| Bug | 严重程度 | 根因 | 修复 |
|---|---|---|---|
| 网络标签页死代码 | 致命 | `alias`/`jinja` 控件创建在 `return` 之后 | 重写整个文件 |
| 下拉框 values() 逻辑反了 | 高 | `startswith("(默认")` 前面缺少 `not` | 加上 `not` |
| 重启时信号泄漏 | 高 | `QueuedConnection` 未断开 | 改为 `SingleShotConnection` |
| 健康检查连了 `0.0.0.0` | 高 | 把 `cfg.host` 传给了健康检查 URL | 硬编码 `127.0.0.1` |
| 速度测试连了 `0.0.0.0` | 高 | 把 `cfg.host` 传给了连接 URL | 硬编码 `127.0.0.1` |
| 日志面板硬编码暗色 | 中 | 浅色主题下文字不可见 | 改为基于调色板的颜色 |
| 采样标签页 0 值不发 changed | 中 | lambda 三元运算符跳过了 emit | 改为元组 `(emit(), ...)` |
| 日志流误判 stderr | 中 | 用 `in` 而不是 `startswith` | 改为 `startswith` |
| cache_prompt 默认被勾选 | 中 | `__init__` 中有 `setChecked(True)` | 删除 |
| PyInstaller 缺隐藏导入 | 中 | `.spec` 没声明 psutil/pynvml 等 | 加到 `hiddenimports` |

## 16. 验收标准（全部达成）

1. ✅ 可通过 GUI 配置所有常用 `llama-server` 参数。
2. ✅ 可保存/加载/重命名/删除命名预设。
3. ✅ 启动/停止/重启 + 实时日志输出 + 健康检查状态灯。
4. ✅ 资源监控以 1Hz 刷新 CPU/RAM/VRAM/GPU%。
5. ✅ 速度测试报告 tok/s、首 token 延迟、token 数。
6. ✅ 主题切换正常（浅色/深色/跟随系统），重启后保持。
7. ✅ 所有快捷键功能正常（`Ctrl+S`、`F5`、`Ctrl+.` 等）。
8. ✅ PyInstaller 产出单文件 `.exe`，含自定义图标。
9. ✅ 40 个 pytest 测试全部通过。
10. ✅ 已推送到 GitHub，含 README 和 .gitignore。
