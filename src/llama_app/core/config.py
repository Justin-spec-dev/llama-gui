"""Configuration dataclass for llama-server command-line arguments.

The Config holds raw values from the UI. ConfigBuilder.to_args() converts a
Config into the list of CLI args suitable for ``QProcess`` / ``subprocess``.

Conventions:
    * ``None``  -> field not emitted (llama-server uses its default).
    * ``False`` on a toggle -> negative flag emitted (e.g. ``--no-mmap``).
    * ``True``  on a toggle -> positive flag emitted (e.g. ``--mlock``).
    * String enums (flash_attn, reasoning) are validated against allowed values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


FlashAttn = Literal["on", "off", "auto"]
Reasoning = Literal["on", "off", "auto"]
SplitMode = Literal["none", "layer", "row", "tensor"]
CacheType = Literal["f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"]


@dataclass
class Config:
    # --- Model ---
    server_path: str            # path to llama-server.exe (used by ServerProcess, not emitted)
    model_path: str             # -m
    mmproj_path: str | None = None

    # --- Performance ---
    n_gpu_layers: int | None = None           # -ngl / --n-gpu-layers
    n_cpu_moe: int | None = None              # -ncmoe
    ctx_size: int | None = None              # -c / --ctx-size
    threads: int | None = None               # -t
    threads_batch: int | None = None         # -tb
    batch_size: int | None = None            # -b
    ubatch_size: int | None = None           # -ub
    cache_type_k: CacheType | None = None     # -ctk
    cache_type_v: CacheType | None = None     # -ctv
    flash_attn: FlashAttn | None = None      # -fa
    mlock: bool = False                      # --mlock
    no_mmap: bool = False                    # --no-mmap
    parallel: int | None = None              # -np
    cont_batching: bool | None = None        # -cb / --no-cont-batching

    # --- Network ---
    host: str | None = None                  # --host
    port: int | None = None                  # --port
    api_key: str | None = None               # --api-key
    enable_ui: bool | None = None            # --ui / --no-ui (None=use server default, True=--ui, False=--no-ui)
    metrics: bool = False                    # --metrics
    alias: str | None = None                 # -a
    jinja: bool | None = None                # --jinja / --no-jinja

    # --- Sampling ---
    n_predict: int | None = None             # -n
    temperature: float | None = None         # --temp
    top_k: int | None = None                 # --top-k
    top_p: float | None = None               # --top-p
    min_p: float | None = None               # --min-p
    repeat_penalty: float | None = None      # --repeat-penalty
    repeat_last_n: int | None = None         # --repeat-last-n
    presence_penalty: float | None = None    # --presence-penalty
    frequency_penalty: float | None = None   # --frequency-penalty
    seed: int | None = None                  # -s
    reasoning: Reasoning | None = None       # --reasoning
    reasoning_budget: int | None = None      # --reasoning-budget

    # --- Advanced ---
    split_mode: SplitMode | None = None      # -sm
    tensor_split: str | None = None          # -ts
    main_gpu: int | None = None              # -mg
    lora: list[str] = field(default_factory=list)
    hf_repo: str | None = None
    hf_file: str | None = None
    hf_token: str | None = None
    timeout: int | None = None               # -to
    verbose: bool = False                    # -v
    log_verbosity: int | None = None         # -lv
    no_warmup: bool = False                  # --no-warmup
    cache_prompt: bool | None = None         # --cache-prompt / --no-cache-prompt
    lookup_cache_static: str | None = None   # -lcs
    lookup_cache_dynamic: str | None = None  # -lcd

    def validate(self) -> None:
        """Validate enums, required nonblank paths, and cross-field relationships."""
        enum_checks = {
            "flash_attn": (self.flash_attn, {"on", "off", "auto"}),
            "reasoning": (self.reasoning, {"on", "off", "auto"}),
            "split_mode": (self.split_mode, {"none", "layer", "row", "tensor"}),
            "cache_type_k": (self.cache_type_k, {"f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"}),
            "cache_type_v": (self.cache_type_v, {"f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"}),
        }
        for name, (value, allowed) in enum_checks.items():
            if value is not None and value not in allowed:
                raise ValueError(f"{name}={value!r} not in {sorted(allowed)}")

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


class ConfigBuilder:
    """Convert a Config into the list of args for llama-server."""

    _INT_FIELDS: dict[str, str] = {
        "n_gpu_layers": "--n-gpu-layers",
        "n_cpu_moe": "--n-cpu-moe",
        "ctx_size": "--ctx-size",
        "threads": "--threads",
        "threads_batch": "--threads-batch",
        "batch_size": "--batch-size",
        "ubatch_size": "--ubatch-size",
        "parallel": "--parallel",
        "n_predict": "--n-predict",
        "top_k": "--top-k",
        "repeat_last_n": "--repeat-last-n",
        "seed": "--seed",
        "main_gpu": "--main-gpu",
        "timeout": "--timeout",
        "log_verbosity": "--log-verbosity",
        "reasoning_budget": "--reasoning-budget",
    }

    _FLOAT_FIELDS: dict[str, str] = {
        "temperature": "--temp",
        "top_p": "--top-p",
        "min_p": "--min-p",
        "repeat_penalty": "--repeat-penalty",
        "presence_penalty": "--presence-penalty",
        "frequency_penalty": "--frequency-penalty",
    }

    _STR_FIELDS: dict[str, str] = {
        "host": "--host",
        "port": "--port",
        "api_key": "--api-key",
        "alias": "-a",
        "tensor_split": "--tensor-split",
        "hf_repo": "--hf-repo",
        "hf_file": "--hf-file",
        "hf_token": "--hf-token",
        "lookup_cache_static": "--lookup-cache-static",
        "lookup_cache_dynamic": "--lookup-cache-dynamic",
        "cache_type_k": "--cache-type-k",
        "cache_type_v": "--cache-type-v",
        "flash_attn": "--flash-attn",
        "reasoning": "--reasoning",
        "split_mode": "--split-mode",
    }

    _BOOL_FLAG_FIELDS: dict[str, str] = {
        "mlock": "--mlock",
        "metrics": "--metrics",
        "verbose": "-v",
        "no_warmup": "--no-warmup",
    }

    _BOOL_NEG_FIELDS: dict[str, str] = {
        "no_mmap": "--no-mmap",
    }

    _TRISTATE_FIELDS: dict[str, tuple[str, str]] = {
        "enable_ui": ("--ui", "--no-ui"),
        "jinja": ("--jinja", "--no-jinja"),
        "cont_batching": ("--cont-batching", "--no-cont-batching"),
        "cache_prompt": ("--cache-prompt", "--no-cache-prompt"),
    }

    @classmethod
    def to_args(cls, cfg: Config) -> list[str]:
        """Convert Config to argv list. Skips None fields."""
        cfg.validate()
        args: list[str] = ["-m", cfg.model_path]

        if cfg.mmproj_path:
            args += ["--mmproj", cfg.mmproj_path]

        for fname, flag in cls._INT_FIELDS.items():
            val = getattr(cfg, fname)
            if val is not None:
                args += [flag, str(val)]

        for fname, flag in cls._FLOAT_FIELDS.items():
            val = getattr(cfg, fname)
            if val is not None:
                args += [flag, str(val)]

        for fname, flag in cls._STR_FIELDS.items():
            val = getattr(cfg, fname)
            if val is not None:
                args += [flag, str(val)]

        for fname, flag in cls._BOOL_FLAG_FIELDS.items():
            if getattr(cfg, fname):
                args.append(flag)

        for fname, neg_flag in cls._BOOL_NEG_FIELDS.items():
            if getattr(cfg, fname):
                args.append(neg_flag)

        for fname, (pos, neg) in cls._TRISTATE_FIELDS.items():
            val = getattr(cfg, fname)
            if val is True:
                args.append(pos)
            elif val is False:
                args.append(neg)

        for lora_path in cfg.lora:
            args += ["--lora", lora_path]

        return args
