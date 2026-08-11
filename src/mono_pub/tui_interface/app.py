from __future__ import annotations

import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.text import Text
from slugify import slugify
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

from mono_pub.commands.open import build_editor_command
from mono_pub.config import load_config
from mono_pub.process.assets import MissingImageError
from mono_pub.process.publish import (
    DirtyPublishRepositoryError,
    GitCommandError,
    GitRepositoryError,
    JekyllCommandError,
    PublishResult,
    publish_type,
)
from mono_pub.process.release import ExistingReleaseError, MissingRequiredFieldsError, release_type
from mono_pub.process.release_config import PATH_KEYS_BY_TYPE

CONTENT_TYPES = (
    ("Post", "post"),
    ("Project", "project"),
    ("Music", "music"),
)


# ── Shared CSS (copied from mono-archive for now; in the future this would be in a common package) ──
COMMON_CSS = """
.section-title {
    text-style: bold;
    margin-bottom: 1;
}

.action-button {
    width: 90%;
    margin-top: 1;
}

.panel {
    border: solid $accent;
    padding: 1;
    margin-bottom: 1;
}

.heading-bar {
    padding: 1 2;
    border-bottom: solid $accent;
}

.status-bar {
    height: auto;
    padding: 1 2;
    border-top: solid $accent;
}

.missing-required {
    color: $error;
    text-style: bold;
}

.success-text {
    color: $success;
}

.warning-text {
    color: $warning;
}

.dim-text {
    color: $text-muted;
}
"""


class MonoPubTuiApp(App):
    CSS = COMMON_CSS + """
    Screen {
        layout: vertical;
    }

    #workspace {
        height: 1fr;
        padding: 1;
    }

    #sidebar {
        width: 34;
        padding-right: 1;
    }

    #main {
        width: 1fr;
    }

    #overview-panel {
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
        height: 2fr;
    }

    #overview-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #output-area {
        height: 1fr;
        border: solid $accent;
        padding: 1;
        margin-top: 1;
    }

    #output-title {
        text-style: bold dim;
        margin-bottom: 1;
    }

    Button {
        width: 90%;
        margin-top: 1;
    }

    #draft-title-input {
        width: 100%;
        margin-top: 1;
    }

    #content-type-label {
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    TITLE = "mono-pub"

    def __init__(self):
        super().__init__()
        self.config: dict | None = None
        self._overview_lines: list[str] = []
        self._output_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="workspace"):
            with Vertical(id="sidebar"):
                with Vertical(classes="panel"):
                    yield Label("Content", classes="section-title")
                    yield Label("", id="content-type-label")
                    yield Select(CONTENT_TYPES, value="post", id="content-type")
                    yield Input(placeholder="Draft title", id="draft-title")
                    yield Button("Create draft", id="create-draft", variant="primary")
                with VerticalScroll(classes="panel"):
                    yield Label("Actions", classes="section-title")
                    yield Button("Open drafts", id="open")
                    yield Button("Release marked drafts", id="release")
                    yield Button("Publish and push", id="publish")
                    yield Button("Refresh", id="refresh")
                    yield Button("Publish No git", id="publish-no-git")
                    yield Button("Dry run preview", id="dry-run")
            with Vertical(id="main"):
                with Vertical(id="overview-panel"):
                    yield Label("Library overview", id="overview-title")
                    yield Static("", id="overview-content")
                with Vertical(id="output-area"):
                    yield Label("Output", id="output-title")
                    yield Static("", id="output-content")
        yield Footer()

    def on_mount(self):
        self.theme = "gruvbox"
        self.load_configuration()
        self.refresh_summary()
        self.update_content_type_label()

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "content-type":
            self.update_content_type_label()

    def update_content_type_label(self):
        label = self.query_one("#content-type-label", Label)
        value = self.query_one("#content-type", Select).value
        if value and value != Select.NULL:
            label.update(f"[dim]Showing {str(value).title()} files[/dim]")
        else:
            label.update("")

    def compose_output(self) -> Static:
        return self.query_one("#output-content", Static)

    def log_output(self, message: str):
        """Append a styled message to the output area."""
        self._output_lines.append(message)
        output = self.compose_output()
        output.update("\\n".join(self._output_lines))
        # Auto-scroll to bottom
        output.scroll_end()

    def clear_output(self):
        self._output_lines = []
        self.compose_output().update("")

    def log_overview(self, message: str):
        self._overview_lines.append(message)
        self.query_one("#overview-content", Static).update("\\n".join(self._overview_lines))

    def action_refresh(self):
        self.load_configuration()
        self.refresh_summary()
        self.app.notify("Refreshed", severity="success")

    def on_button_pressed(self, event: Button.Pressed):
        actions = {
            "create-draft": self.create_draft,
            "open": self.open_selected,
            "release": self.release_selected,
            "publish-no-git": lambda: self.publish_selected(no_git=True),
            "publish": lambda: self.publish_selected(),
            "dry-run": lambda: self.publish_selected(no_git=True, dry_run=True),
            "refresh": self.action_refresh,
        }

        action = actions.get(event.button.id or "")
        if action is not None:
            action()

    def load_configuration(self):
        try:
            self.config = load_config()
        except Exception as error:
            self.config = None
            self.app.notify(f"Configuration error: {error}", severity="error")

    def refresh_summary(self):
        self._overview_lines = []
        self.query_one("#overview-content", Static).update("")

        if self.config is None:
            self.log_overview("[red]Configuration could not be loaded.[/red]")
            return

        self.log_overview("[b]Library overview[/b]")
        for content_type in PATH_KEYS_BY_TYPE:
            path_key = PATH_KEYS_BY_TYPE[content_type]
            self.write_file_group(content_type, "Drafts", "drafts_path", path_key)
            self.write_file_group(content_type, "Releases", "releases_path", path_key)

    def write_file_group(
        self,
        content_type: str,
        label: str,
        group_key: str,
        path_key: str,
    ):
        from rich.markup import escape as rich_escape

        files = self.markdown_files(group_key, path_key)
        self.log_overview(
            f"\n[b]{rich_escape(content_type.title())} {rich_escape(label)} ({len(files)})[/b]"
        )

        if not files:
            self.log_overview("  [dim]No files[/dim]")
            return

        for file in files:
            self.log_overview(f"  {rich_escape(file.name)}")

    def create_draft(self):
        if self.config is None:
            self.app.notify("Cannot create a draft until configuration loads.", severity="error")
            return

        content_type = self.selected_content_type()
        title_input = self.query_one("#draft-title", Input)
        title = title_input.value.strip()

        if not title:
            self.app.notify("Enter a title before creating a draft.", severity="warning")
            return

        try:
            target = create_draft(self.config, content_type, title)
        except FileExistsError as error:
            path = error.filename or error.args[0]
            self.app.notify(f"Draft already exists: {path}", severity="error")
            return
        except Exception as error:
            self.app.notify(f"Could not create draft: {error}", severity="error")
            return

        title_input.value = ""
        self.clear_output()
        self.log_output(f"[green]Created draft:[/green] {target}")
        self.refresh_summary()
        self.app.notify(f"Created: {target.name}", severity="success")

    def open_selected(self):
        if self.config is None:
            self.app.notify("Cannot open drafts until configuration loads.", severity="error")
            return

        content_type = self.selected_content_type()
        path_key = PATH_KEYS_BY_TYPE[content_type]
        editor_command = self.config.get("editor_command")

        if not editor_command:
            self.app.notify("Missing editor_command in configuration.", severity="error")
            return

        draft_path = Path(self.config["drafts_path"][path_key])

        if not draft_path.exists():
            self.app.notify(f"Draft path does not exist: {draft_path}", severity="error")
            return

        try:
            command = build_editor_command(editor_command, draft_path)
            subprocess.Popen(command)
        except FileNotFoundError:
            self.app.notify(f"Editor command not found: {command[0]}", severity="error")
            return
        except ValueError as error:
            self.app.notify(f"Could not open drafts: {error}", severity="error")
            return

        self.clear_output()
        self.log_output(f"[green]Opened drafts:[/green] {draft_path}")
        self.app.notify(f"Opened: {draft_path}", severity="success")

    def release_selected(self):
        if self.config is None:
            self.app.notify("Cannot release until configuration loads.", severity="error")
            return

        self.clear_output()
        content_type = self.selected_content_type()
        self.log_output(f"[b]Releasing {content_type} drafts...[/b]")

        try:
            released = release_type(self.config, content_type)
        except MissingRequiredFieldsError as error:
            self.log_output(f"[red]Missing {error.fields}:[/red] {error.path}")
            self.app.notify(f"Missing fields: {error.fields}", severity="error")
            return
        except ExistingReleaseError as error:
            self.log_output(f"[red]Release already exists:[/red] {error.path}")
            self.app.notify(f"Release already exists: {error.path}", severity="error")
            return
        except MissingImageError as error:
            self.log_output(f"[red]Image not found:[/red] {error.path}")
            self.app.notify(f"Image not found: {error.path}", severity="error")
            return
        except Exception as error:
            self.log_output(f"[red]Release failed:[/red] {error}")
            self.app.notify(f"Release failed: {error}", severity="error")
            return

        if not released:
            self.log_output(f"[dim]No marked {content_type} drafts to release.[/dim]")
            self.app.notify(f"No marked {content_type} drafts to release.", severity="warning")
        else:
            self.log_output(f"[green]Released {len(released)} {content_type} draft(s).[/green]")
            for path in released:
                self.log_output(f"  {path}")
            self.app.notify(f"Released {len(released)} draft(s)", severity="success")

        self.refresh_summary()

    def publish_selected(self, *, no_git: bool = False, dry_run: bool = False):
        if self.config is None:
            self.app.notify("Cannot publish until configuration loads.", severity="error")
            return

        self.clear_output()
        content_type = self.selected_content_type()
        mode = "dry run" if dry_run else ("publish (no git)" if no_git else "publish and push")
        self.log_output(f"[b]Publishing {content_type} ({mode})...[/b]")

        try:
            result = publish_type(
                self.config,
                content_type,
                copy_files=True,
                run_git=not no_git and not dry_run,
                dry_run=dry_run,
            )
        except DirtyPublishRepositoryError as error:
            self.log_output(f"[red]Publish repository is dirty:[/red] {error.base_dir}")
            self.log_output(error.status)
            self.app.notify("Publish repository is dirty", severity="error")
            return
        except (GitCommandError, GitRepositoryError, JekyllCommandError) as error:
            self.log_output(f"[red]{error}[/red]")
            if error.output:
                self.log_output(error.output)
            self.app.notify(str(error), severity="error")
            return
        except Exception as error:
            self.log_output(f"[red]Publish failed:[/red] {error}")
            self.app.notify(f"Publish failed: {error}", severity="error")
            return

        self.report_publish_result(result)
        self.refresh_summary()

    def report_publish_result(self, result: PublishResult):
        from rich.markup import escape as rich_escape

        self.log_output(
            f"[green]Published {len(result.files)} {result.content_type} files "
            f"and {len(result.asset_dirs)} asset directories.[/green]"
        )

        for path in result.files:
            self.log_output(f"  {rich_escape(str(path))}")

        for path in result.asset_dirs:
            self.log_output(f"  {rich_escape(str(path))}")

        if result.git is not None:
            self.log_output(f"[dim]{rich_escape(result.git.message)}[/dim]")

        if result.jekyll is not None:
            self.log_output(
                f"Jekyll server started on http://127.0.0.1:{result.jekyll.port}"
            )

        self.app.notify(
            f"Published {len(result.files)} file(s)",
            severity="success",
        )

    def markdown_files(self, group_key: str, path_key: str) -> list[Path]:
        path = Path(self.config[group_key][path_key])
        return sorted(path.glob("*.md")) if path.exists() else []

    def selected_content_type(self) -> str:
        value = self.query_one("#content-type", Select).value
        return str(value)


def create_draft(config: dict, content_type: str, title: str) -> Path:
    from datetime import date

    slug = slugify(title)
    path_key = PATH_KEYS_BY_TYPE[content_type]
    target_dir = Path(config["drafts_path"][path_key])
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{date.today().isoformat()}-{slug}.md"

    if target.exists():
        raise FileExistsError(target)

    env = Environment(loader=FileSystemLoader(config["templates_path"]))
    template = env.get_template(f"{content_type}.md.j2")
    context = {
        "title": title,
        "date": date.today().isoformat(),
        "author": config["author"],
        "type": content_type,
    }

    if content_type == "music":
        context["permalink"] = slug

    target.write_text(template.render(**context), encoding="utf-8")
    return target
