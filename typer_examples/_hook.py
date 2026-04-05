from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import click

import typer.rich_utils as _ut

from ._models import ExamplesConfig

_MARKER = "_typer_examples_installed"

_config: ExamplesConfig = ExamplesConfig()


def get_config() -> ExamplesConfig:
    return _config


def set_config(cfg: ExamplesConfig) -> None:
    global _config
    _config = cfg


def install_hook() -> None:
    if getattr(_ut, _MARKER, False):
        return

    _upstream = _ut.rich_format_help

    def _patched(
        *, obj: "click.Command", ctx: "click.Context", markup_mode: str
    ) -> None:
        _upstream(obj=obj, ctx=ctx, markup_mode=markup_mode)
        _render_examples(obj, ctx)

    _ut.rich_format_help = _patched  # type: ignore[assignment]
    setattr(_ut, _MARKER, True)


def _render_examples(obj: "click.Command", ctx: "click.Context") -> None:
    from ._renderer import print_examples_panel

    examples = getattr(getattr(obj, "callback", None), "_typer_examples", None)
    if not examples:
        return

    print_examples_panel(examples, obj, ctx)
