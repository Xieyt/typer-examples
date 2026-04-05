from __future__ import annotations

import typer
import typer.rich_utils as ut
from typer.testing import CliRunner

from typer_examples import ExamplesConfig, configure, example, get_all_examples, install
from typer_examples._models import Example
from typer_examples._providers import resolve_vars, safe_format_map

runner = CliRunner()


def _fresh_app() -> typer.Typer:
    return typer.Typer(name="cli")


class TestExampleDecorator:
    def test_attaches_examples_to_function(self):
        @example("Do a thing", "cli thing")
        def fn():
            pass

        assert hasattr(fn, "_typer_examples")
        assert len(fn._typer_examples) == 1
        ex = fn._typer_examples[0]
        assert ex.desc == "Do a thing"
        assert ex.code == "cli thing"
        assert ex.detail == ""

    def test_multiple_examples_stacked(self):
        @example("Second", "cli second")
        @example("First", "cli first")
        def fn():
            pass

        assert len(fn._typer_examples) == 2
        assert fn._typer_examples[0].desc == "Second"
        assert fn._typer_examples[1].desc == "First"

    def test_example_with_detail(self):
        @example("With detail", "cli foo", detail="Extra info here.")
        def fn():
            pass

        assert fn._typer_examples[0].detail == "Extra info here."

    def test_example_with_per_example_vars(self):
        @example("Named", "cli create {name}", name="myapp")
        def fn():
            pass

        assert fn._typer_examples[0].vars == {"name": "myapp"}


class TestInstallHook:
    def test_install_patches_rich_format_help(self):
        original = ut.rich_format_help
        app = _fresh_app()
        install(app)
        assert ut.rich_format_help is not original or getattr(
            ut, "_typer_examples_installed", False
        )

    def test_install_is_idempotent(self):
        app = _fresh_app()
        install(app)
        fn_after_first = ut.rich_format_help
        install(app)
        assert ut.rich_format_help is fn_after_first


class TestSafeFormatMap:
    def test_fills_known_placeholder(self):
        assert safe_format_map("hello {name}", {"name": "world"}) == "hello world"

    def test_leaves_unknown_placeholder_intact(self):
        assert safe_format_map("hello {unknown}", {}) == "hello {unknown}"

    def test_mixed_known_and_unknown(self):
        result = safe_format_map("{a} and {b}", {"a": "foo"})
        assert result == "foo and {b}"


class TestResolveVars:
    def _make_command_and_ctx(self, with_arg: bool = True):
        import click

        params = [click.Argument(["name"])] if with_arg else []
        cmd = click.Command("create", params=params, callback=lambda **kw: None)
        ctx = click.Context(cmd)
        return cmd, ctx

    def test_returns_empty_for_no_params(self):
        cmd, ctx = self._make_command_and_ctx(with_arg=False)
        result = resolve_vars(cmd, ctx, {})
        assert result == {}

    def test_config_vars_string(self):
        cmd, ctx = self._make_command_and_ctx(with_arg=False)
        result = resolve_vars(cmd, ctx, {"version": "1.0.0"})
        assert result["version"] == "1.0.0"

    def test_config_vars_callable(self):
        cmd, ctx = self._make_command_and_ctx(with_arg=False)
        result = resolve_vars(cmd, ctx, {"version": lambda ctx: "2.0"})
        assert result["version"] == "2.0"

    def test_config_vars_callable_exception_is_ignored(self):
        cmd, ctx = self._make_command_and_ctx(with_arg=False)
        result = resolve_vars(
            cmd, ctx, {"bad": lambda ctx: (_ for _ in ()).throw(RuntimeError("oops"))}
        )
        assert "bad" not in result


class TestExamplesConfig:
    def test_defaults(self):
        cfg = ExamplesConfig()
        assert cfg.panel_title == "Examples"
        assert cfg.syntax_highlight is True
        assert cfg.show_command_prefix is True
        assert cfg.heading_style == "bold"
        assert cfg.detail_style == "dim"

    def test_configure_sets_global(self):
        from typer_examples._hook import get_config

        configure(ExamplesConfig(panel_title="My Examples"))
        assert get_config().panel_title == "My Examples"
        configure(ExamplesConfig())


class TestGetAllExamples:
    def test_collects_from_registered_commands(self):
        app = _fresh_app()

        @app.command()
        @example("Do something", "cli do")
        def do_something():
            pass

        result = get_all_examples(app)
        assert ("do-something",) in result
        assert result[("do-something",)][0].desc == "Do something"

    def test_collects_from_subapp(self):
        app = _fresh_app()
        sub = typer.Typer()

        @sub.command()
        @example("Sub action", "cli sub action")
        def action():
            pass

        app.add_typer(sub, name="sub")
        result = get_all_examples(app)
        assert ("sub", "action") in result

    def test_empty_when_no_examples(self):
        app = _fresh_app()

        @app.command()
        def plain():
            pass

        result = get_all_examples(app)
        assert result == {}


class TestHelpRendering:
    def test_help_output_contains_examples_panel(self):
        app = _fresh_app()
        install(app)

        @app.command()
        @example("Say hello", "cli greet --name Alice")
        def greet(name: str = "World"):
            typer.echo(f"Hello {name}")

        result = runner.invoke(app, ["greet", "--help"])
        assert "Examples" in result.output
        assert "Say hello" in result.output

    def test_no_examples_no_panel(self):
        app = _fresh_app()
        install(app)

        @app.command()
        def quiet():
            pass

        result = runner.invoke(app, ["quiet", "--help"])
        assert "Examples" not in result.output
