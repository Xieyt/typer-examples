from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Callable, Optional

import typer as _typer

from ._hook import install_hook, register_app, set_config
from ._models import Example, ExamplesConfig
from .docs import get_all_examples

__all__ = [
    "example",
    "install",
    "configure",
    "ExamplesConfig",
    "get_all_examples",
]

try:
    __version__ = _pkg_version("typer-examples")
except PackageNotFoundError:  # source tree, not installed
    __version__ = "0.0.0.dev0"


def example(
    desc: str,
    code: str,
    detail: str = "",
    **vars: str,
) -> Callable:
    ex = Example(desc=desc, code=code, detail=detail, vars=vars)

    def decorator(fn: Callable) -> Callable:
        if not hasattr(fn, "_typer_examples"):
            fn._typer_examples = []  # type: ignore[attr-defined]
        fn._typer_examples.insert(0, ex)  # type: ignore[attr-defined]
        return fn

    return decorator


def install(app: _typer.Typer, config: Optional[ExamplesConfig] = None) -> None:
    cfg = config or ExamplesConfig()
    register_app(app, cfg)
    install_hook()


def configure(config: ExamplesConfig) -> None:
    set_config(config)
