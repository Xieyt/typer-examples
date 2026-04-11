from __future__ import annotations

import sys
from typing import Any, Dict

import click

# Click uses a Sentinel singleton (not None) for required args that have no default.
# We must exclude it from the template-var resolution, otherwise str(Sentinel.UNSET)
# leaks as a literal "Sentinel.UNSET" placeholder value.
try:
    from click.core import Sentinel as _ClickSentinel

    _CLICK_UNSET = _ClickSentinel.UNSET
except (ImportError, AttributeError):
    # Older Click versions don't have this sentinel; use a private object that
    # will never match any real default value.
    _CLICK_UNSET = object()


class _SafeFormatMap(dict):
    """dict subclass that returns '{key}' for missing keys instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def resolve_vars(
    obj: click.Command,
    ctx: click.Context,
    config_vars: Dict[str, Any],
) -> Dict[str, str]:
    """Build the template-variable mapping for a single render pass.

    Resolution priority (highest → lowest):
    1. Auto-fill from ``sys.argv`` positional args before ``--help`` (merged by
       the renderer after this returns, always wins over per-example kwargs)
    2. Per-example kwargs (merged by the renderer after this returns)
    3. App-level ``configure(vars={...})`` — callables evaluated here
    4. Parameter defaults from the Click command definition
    """
    result: Dict[str, str] = {}

    positional_params = [p for p in obj.params if isinstance(p, click.Argument)]

    for param in positional_params:
        if param.default is not None and param.default is not _CLICK_UNSET:
            result[param.name] = str(param.default)  # type: ignore[arg-type]

    argv_values = _extract_argv_positionals(obj, ctx)
    result.update(argv_values)

    for key, val in config_vars.items():
        if callable(val):
            try:
                result[key] = str(val(ctx))
            except Exception:
                pass
        else:
            result[key] = str(val)

    return result


def _extract_argv_positionals(
    obj: click.Command,
    ctx: click.Context,
) -> Dict[str, str]:
    positional_params = [p for p in obj.params if isinstance(p, click.Argument)]
    if not positional_params:
        return {}

    known_subcommands: set[str] = set()
    c: click.Context | None = ctx
    while c is not None:
        if isinstance(c.command, click.MultiCommand):
            known_subcommands.update(c.command.list_commands(c))
        c = c.parent

    raw_args = list(sys.argv[1:])
    try:
        help_idx = next(i for i, a in enumerate(raw_args) if a in ("--help", "-h"))
        raw_args = raw_args[:help_idx]
    except StopIteration:
        pass

    command_path_tokens = ctx.command_path.split()[1:]
    for token in command_path_tokens:
        if raw_args and raw_args[0] == token:
            raw_args = raw_args[1:]

    positional_values = [a for a in raw_args if not a.startswith("-") and a not in known_subcommands]

    result: Dict[str, str] = {}
    for param, value in zip(positional_params, positional_values):
        result[param.name] = value  # type: ignore[assignment]

    return result


def safe_format_map(text: str, vars: Dict[str, str]) -> str:
    return text.format_map(_SafeFormatMap(vars))
