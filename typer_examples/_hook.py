from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import click

import typer.rich_utils as _ut

from ._models import ExamplesConfig

_MARKER = "_typer_examples_installed"

_config: ExamplesConfig = ExamplesConfig()

_app_config_map: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def get_config() -> ExamplesConfig:
    return _config


def set_config(cfg: ExamplesConfig) -> None:
    global _config
    _config = cfg


def register_app(app: Any, cfg: ExamplesConfig) -> None:
    _app_config_map[app] = cfg


def _get_config_for_callback(callback: Any) -> ExamplesConfig:
    original = callback
    while hasattr(original, "__wrapped__"):
        original = original.__wrapped__

    for app, cfg in list(_app_config_map.items()):
        if _app_directly_has_callback(app, original):
            return cfg
    return _config


def _app_directly_has_callback(app: Any, callback: Any) -> bool:
    for cmd_info in app.registered_commands:
        if cmd_info.callback is callback:
            return True
    return False


def install_hook() -> None:
    try:
        import rich  # noqa: F401
    except ImportError:
        return

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
    try:
        from ._renderer import print_examples_panel
    except ImportError:
        return

    examples = getattr(getattr(obj, "callback", None), "_typer_examples", None)
    if not examples:
        return

    config = _get_config_for_callback(obj.callback)
    print_examples_panel(examples, obj, ctx, config)
