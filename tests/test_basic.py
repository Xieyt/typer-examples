from __future__ import annotations

import typer
import typer.rich_utils as ut
from typer.testing import CliRunner

from typer_examples import ExamplesConfig, configure, example, get_all_examples, install
from typer_examples._models import Example
from typer_examples._providers import resolve_vars, safe_format_map
from typer_examples.docs import to_markdown, to_rst

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
        assert ut.rich_format_help is not original or getattr(ut, "_typer_examples_installed", False)

    def test_install_is_idempotent(self):
        app = _fresh_app()
        install(app)
        fn_after_first = ut.rich_format_help
        install(app)
        assert ut.rich_format_help is fn_after_first

    def test_install_stores_config_on_app(self):
        from typer_examples._hook import _app_config_map

        app = _fresh_app()
        cfg = ExamplesConfig(panel_title="Custom")
        install(app, config=cfg)
        assert _app_config_map[app].panel_title == "Custom"

    def test_install_default_config_when_none_given(self):
        from typer_examples._hook import _app_config_map

        app = _fresh_app()
        install(app)
        assert _app_config_map[app].panel_title == "Examples"


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
        result = resolve_vars(cmd, ctx, {"bad": lambda ctx: (_ for _ in ()).throw(RuntimeError("oops"))})
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

    def test_per_app_config_used_in_help(self):
        app = _fresh_app()
        install(app, config=ExamplesConfig(panel_title="App Docs"))

        @app.command()
        @example("Say hello", "cli greet")
        def greet():
            pass

        result = runner.invoke(app, ["greet", "--help"])
        assert "App Docs" in result.output

    def test_two_apps_use_independent_configs(self):
        app_a = _fresh_app()
        app_b = typer.Typer(name="other")
        install(app_a, config=ExamplesConfig(panel_title="App A"))
        install(app_b, config=ExamplesConfig(panel_title="App B"))

        @app_a.command()
        @example("Action A", "cli action")
        def action_a():
            pass

        @app_b.command()
        @example("Action B", "other action")
        def action_b():
            pass

        result_a = runner.invoke(app_a, ["action-a", "--help"])
        result_b = runner.invoke(app_b, ["action-b", "--help"])
        assert "App A" in result_a.output
        assert "App B" in result_b.output


class TestDocsVarsParam:
    def _app_with_example(self) -> typer.Typer:
        app = _fresh_app()

        @app.command()
        @example("Deploy to env", "{env} --tag {version}")
        def deploy(env: str):
            pass

        return app

    def test_to_markdown_no_vars_leaves_placeholders(self):
        app = self._app_with_example()
        md = to_markdown(app)
        assert "{env}" in md
        assert "{version}" in md

    def test_to_markdown_with_vars_resolves_placeholders(self):
        app = self._app_with_example()
        md = to_markdown(app, vars={"env": "staging", "version": "2.0"})
        assert "staging" in md
        assert "2.0" in md
        assert "{env}" not in md

    def test_to_rst_no_vars_leaves_placeholders(self):
        app = self._app_with_example()
        rst = to_rst(app)
        assert "{env}" in rst

    def test_to_rst_with_vars_resolves_placeholders(self):
        app = self._app_with_example()
        rst = to_rst(app, vars={"env": "prod", "version": "3.1"})
        assert "prod" in rst
        assert "{env}" not in rst

    def test_per_example_vars_override_docs_vars(self):
        app = _fresh_app()

        @app.command()
        @example("Override test", "{env}", env="hardcoded")
        def cmd(env: str):
            pass

        md = to_markdown(app, vars={"env": "global"})
        assert "hardcoded" in md
        assert "global" not in md


class TestArgvWinsOverPerExampleKwargs:
    def test_argv_value_beats_per_example_kwarg(self):
        import sys

        app = _fresh_app()
        install(app)

        @app.command()
        @example("Create bench", "{name}", name="fallback")
        def create(name: str):
            pass

        original_argv = sys.argv[:]
        try:
            sys.argv = ["create", "myvalue", "--help"]
            result = runner.invoke(app, ["create", "myvalue", "--help"])
        finally:
            sys.argv = original_argv

        assert "myvalue" in result.output
        assert "fallback" not in result.output

    def test_per_example_kwarg_used_as_fallback_when_no_argv(self):
        import sys

        app = _fresh_app()
        install(app)

        @app.command()
        @example("Create bench", "{name}", name="fallback")
        def create(name: str):
            pass

        original_argv = sys.argv[:]
        try:
            sys.argv = ["create", "--help"]
            result = runner.invoke(app, ["create", "--help"])
        finally:
            sys.argv = original_argv

        assert "fallback" in result.output

    def test_subcommand_token_not_mistaken_for_positional(self):
        import sys
        import click
        from typer_examples._providers import _extract_argv_positionals

        cmd = click.Command("create", params=[click.Argument(["name"])], callback=lambda **kw: None)
        parent_ctx = click.Context(click.Group("sub"), info_name="sub")
        ctx = click.Context(cmd, info_name="create", parent=parent_ctx)

        original_argv = sys.argv[:]
        try:
            sys.argv = ["cli", "sub", "create", "--help"]
            result = _extract_argv_positionals(cmd, ctx)
        finally:
            sys.argv = original_argv

        assert result == {}

    def test_subcommand_token_with_positional_extracted(self):
        import sys
        import click
        from typer_examples._providers import _extract_argv_positionals

        cmd = click.Command("create", params=[click.Argument(["name"])], callback=lambda **kw: None)
        parent_ctx = click.Context(click.Group("sub"), info_name="sub")
        ctx = click.Context(cmd, info_name="create", parent=parent_ctx)

        original_argv = sys.argv[:]
        try:
            sys.argv = ["cli", "sub", "create", "myvalue", "--help"]
            result = _extract_argv_positionals(cmd, ctx)
        finally:
            sys.argv = original_argv

        assert result == {"name": "myvalue"}
