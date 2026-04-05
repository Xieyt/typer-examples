"""Data models for typer-examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple, Union


@dataclass
class Example:
    """A single CLI usage example attached to a command.

    Attributes:
        desc:   Short heading (5-8 words, imperative). Answers: *what is this example for?*
        code:   The CLI invocation string. May contain ``{placeholder}`` template variables.
        detail: Optional prose line. Answers: *why or when to use this invocation?*
        vars:   Per-example template variable overrides (highest priority in resolution chain).
    """

    desc: str
    code: str
    detail: str = ""
    vars: Dict[str, str] = field(default_factory=dict)


# Template var values can be a plain string or a lazy callable(ctx) -> str
VarValue = Union[str, Callable[..., str]]


@dataclass
class ExamplesConfig:
    """Global rendering configuration for typer-examples.

    Style fields that are ``None`` are auto-matched to the values Typer itself uses
    (read from ``typer.rich_utils`` at render time).
    """

    panel_title: str = "Examples"
    panel_border_style: Optional[str] = None
    panel_padding: Optional[Tuple[Any, ...]] = None
    title_align: Optional[str] = None
    heading_style: str = "bold"
    detail_style: str = "dim"
    syntax_theme: str = "ansi_dark"
    syntax_highlight: bool = True
    show_command_prefix: bool = True
    vars: Dict[str, VarValue] = field(default_factory=dict)
