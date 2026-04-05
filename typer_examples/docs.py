from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import typer

from ._providers import safe_format_map


def get_all_examples(app: typer.Typer) -> Dict[Tuple[str, ...], list]:
    from ._models import Example

    result: Dict[Tuple[str, ...], List[Example]] = {}
    _collect(app, path=(), result=result)
    return result


def _collect(
    app: typer.Typer,
    path: Tuple[str, ...],
    result: Dict[Tuple[str, ...], list],
) -> None:
    for command_info in app.registered_commands:
        name = command_info.name or (
            command_info.callback.__name__.replace("_", "-")
            if command_info.callback
            else None
        )
        if not name:
            continue
        examples = getattr(command_info.callback, "_typer_examples", None)
        if examples:
            result[path + (name,)] = list(examples)

    for group_info in app.registered_groups:
        sub_app = group_info.typer_instance
        if sub_app is None:
            continue
        group_name = group_info.name or ""
        _collect(sub_app, path + (group_name,) if group_name else path, result)


def to_markdown(app: typer.Typer, vars: Optional[Dict[str, str]] = None) -> str:
    all_examples = get_all_examples(app)
    lines: List[str] = []

    for path, examples in all_examples.items():
        command_str = " ".join(path)
        lines.append(f"## `{command_str}`\n")
        for ex in examples:
            lines.append(f"**{ex.desc}**\n")
            if ex.detail:
                lines.append(f"{ex.detail}\n")
            code = (
                safe_format_map(ex.code, {**vars, **ex.vars})
                if vars is not None
                else ex.code
            )
            lines.append(f"```bash\n$ {code}\n```\n")

    return "\n".join(lines)


def to_rst(app: typer.Typer, vars: Optional[Dict[str, str]] = None) -> str:
    all_examples = get_all_examples(app)
    lines: List[str] = []

    for path, examples in all_examples.items():
        command_str = " ".join(path)
        heading = f"``{command_str}``"
        lines.append(heading)
        lines.append("~" * len(heading))
        lines.append("")

        for ex in examples:
            lines.append(f"**{ex.desc}**")
            lines.append("")
            if ex.detail:
                lines.append(ex.detail)
                lines.append("")
            lines.append(".. code-block:: bash")
            lines.append("")
            code = (
                safe_format_map(ex.code, {**vars, **ex.vars})
                if vars is not None
                else ex.code
            )
            lines.append(f"   $ {code}")
            lines.append("")

    return "\n".join(lines)
