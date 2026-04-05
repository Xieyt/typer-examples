from __future__ import annotations

from typing import Any, Callable, List, Optional

import typer

from ._hook import install_hook, set_config
from ._models import Example, ExamplesConfig
from .docs import get_all_examples

__all__ = [
    "example",
    "install",
    "configure",
    "ExamplesConfig",
    "get_all_examples",
]

__version__ = "0.1.0"


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


def install(app: Optional[typer.Typer] = None) -> None:
    install_hook()


def configure(config: ExamplesConfig) -> None:
    set_config(config)
