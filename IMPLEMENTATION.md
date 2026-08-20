# mono-pub — Implementation Documentation

> **mono-pub** is a content publishing tool for [monointerferenz](https://www.monointerferenz.de/) that prepares and publishes Jekyll content via a CLI and an optional Textual TUI.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [CLI Commands](#cli-commands)
5. [Content Types](#content-types)
6. [Jinja2 Templates](#jinja2-templates)
7. [Release Process](#release-process)
8. [Publish Process](#publish-process)
9. [TUI Interface](#tui-interface)
10. [Dependency Overview](#dependency-overview)

---

## Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Publish content (posts, projects, music) for monointerferenz via Jekyll |
| **Language** | Python 3.13+ |
| **Package** | `mono_pub` |
| **Entry point** | `mono-pub` (maps to `mono_pub.main:app`) |
| **CLI framework** | Typer |
| **TUI framework** | Textual (optional `tui` extra) |
| **Template engine** | Jinja2 |

---

## Architecture

```
mono-pub/
├── src/mono_pub/                          # Main package
│   ├── __init__.py                      # Package version (0.1.0)
│   ├── config.py                        # Configuration loading
│   ├── main.py                          # CLI router
│   ├── commands/                        # All CLI subcommands
│   │   ├── __init__.py                  # Entry: Typer() with all subcommand types
│   │   ├── new.py                       # Create new draft content
│   │   ├── list.py                      # List draft / released content
│   │   ├── open.py                      # Open draft folder in editor
│   │   ├── publish.py                   # Publish to Jekyll via git
│   │   ├── release.py                   # Prepare draft files for release
│   │   └── tui.py                       # Launch Textual TUI
│   ├── process/                         # Core business logic
│   │   ├── __init__.py
│   │   ├── compile.py                   # Compile draft frontmatter
│   │   ├── release.py                   # Release content (marked `release: true`)
│   │   ├── release_config.py            # Release rules & path keys
│   │   ├── publish.py                   # Publish files + git push + Jekyll preview
│   │   ├── assets.py                    # Image consolidation & URL rewriting
│   │   └── validate.py                  # Frontmatter validation
│   ├── templates/                       # Jinja2 Jekyll frontmatter templates
│   │   ├── post.md.j2
│   │   ├── project.md.j2
│   │   └── music.md.j2
│   ├── tui_interface/                   # Textual GUI
│   │   ├── __init__.py
│   │   ├── app.py                       # MonoPubTuiApp with lifecycle hooks
│   │   └── ui.py                        # UI layout
│   └── assets/                          # Local asset resources
```

---

## Configuration

Configuration is loaded from `configuartion.yaml` with a three-level resolution strategy:

1. **Explicit path** (`--config` flag)
2. **Environment variable** (`MONO_PUB_CONFIG`)
3. **Working-directory-local config** (`<project-root>/../configuartion.yaml`)
4. **Fallback** (`$HOME/configuartion.yaml`)

### Configuration Schema

```yaml
# Required
author: "Author Name"

# Path groups
drafts_path:
  posts: "path/to/drafts/posts"
  projects: "path/to/drafts/projects"
  music: "path/to/drafts/music"

releases_path:
  posts: "path/to/releases/posts"
  projects: "path/to/releases/projects"
  music: "path/to/releases/music"

assets_path:
  posts: "path/to/assets/posts"
  projects: "path/to/assets/projects"
  music: "path/to/assets/music"

publish_base:
  posts: "path/to/jekyll/content/posts"
  projects: "path/to/jekyll/content/projects"
  music: "path/to/jekyll/content/music"

publish_path:
  posts: "path/to/jekyll/_posts"
  projects: "path/to/jekyll/_projects"
  music: "path/to/jekyll/_music"

publish_assets_path:
  posts: "path/to/jekyll/assets/posts"
  projects: "path/to/jekyll/assets/projects"
  music: "path/to/jekyll/assets/music"

# Optional
editor_command: "vim {path}"        # Shell command to open a draft
release:
  # Overrides default release config
  required_fields:
    posts: ["short_description"]
  build_fields: ["release", "validate", "draft_only"]
  frontmatter_image_fields: ["image_preview"]
  category_fields: ["categories"]
  preserve_string_fields: ["title", "short_description"]
templates_path: "path/to/templates"
```

### `config.py` — Key Logic

```python
def load_config(path: str | None = None) -> dict[str, Any]:
    """Load config from file → env var → working dir → home."""
    config_path = resolve_config_path(path)
    with open(config_path) as file:
        raw = yaml.safe_load(file) or {}
    return _resolve_config_paths(raw, config_path.parent)
```

- `_resolve_config_paths` expands `~` and converts relative paths to absolute based on the config file's directory.
- Path keys (e.g. `drafts_path`) are dict-of-dict under groups, while single path keys (e.g. `templates_path`) are strings.

---

## CLI Commands

All commands are organized under Typer Typer subcommands in `commands/__init__.py`:

```
app.add_typer(new_app,   name="new")
app.add_typer(open_app,  name="open")
app.add_typer(list_app,  name="list")
app.add_typer(release_app, name="release")
app.add_typer(publish_app, name="publish")
app.add_typer(tui_app,   name="tui")
```

### `mono-pub new <type> <title>`

Creates a new draft file in the `drafts_path/<type>` directory.

- **`post`** → `drafts_path/posts/`
- **`project`** → `drafts_path/projects/`
- **`music`** → `drafts_path/music/`

**File naming:** `{YYYY-MM-DD}-{slugified-title}.md`

**Logic (`commands/new.py`):**

```python
def file_operation(title: str, path: Path, content_type: str):
    slug = slugify(title)
    filename = f"{date.today().isoformat()}-{slug}.md"
    env = Environment(loader=FileSystemLoader(config["templates_path"]))
    content = env.get_template(f"{content_type}.md.j2").render(
        title=title, date=today.isoformat(),
        author=config["author"], type=content_type,
        permalink=slug if content_type == "music" else None,
    )
    (path / filename).write_text(content, "utf-8")
```

### `mono-pub list [draft|release] [post|project|music]`

Lists markdown files under the configured draft or release directories.

- `list` → lists all content types (drafts and releases)
- `list draft` → drafts only
- `list release` → releases only
- `list draft post` → draft posts only

**Logic (`commands/list.py`):**

```python
def list_content_type(label: str, config_key: str, content_type: str):
    config = load_config()
    path_key = PATH_KEYS_BY_TYPE[content_type]  # e.g. "posts"
    path = Path(config[config_key][path_key])
    files = sorted(path.glob("*.md"))
    echo(f"{label.capitalize()} {content_type}: {len(files)}")
    for file in files: echo(f"  {file.name}")
```

### `mono-pub open <type>`

Opens the draft folder for the given content type in the configured editor (`editor_command`).

- Validates that the draft path exists.
- Uses shell escaping (`shlex.split`) for the editor command.
- Supports `{path}` placeholder in the editor command string.

### `mono-pub release <type|all>`

Moves drafts marked with `release: true` in frontmatter into the releases directory.

**Validation:**
1. Required frontmatter fields are present (`title`, `date`, `author`, etc.)
2. Referenced images exist
3. A release target does not already exist

**Logic (`commands/release.py` → `process/release.py`):**

```python
def release_type(config, content_type) -> list[Path]:
    drafts = list(drafts_dir.glob("*.md"))
    marked = [p for p in drafts if is_marked_for_release(p)]

    return [release_draft(p, releases_dir, assets_dir, release_config, content_type)
            for p in marked]

def release_draft(path, target_dir, assets_dir, release_config, content_type) -> Path:
    post = frontmatter.load(path)
    missing = missing_required_fields(post, release_config, content_type)
    if missing: raise MissingRequiredFieldsError(path, missing)

    compiled = compile_draft(post, path, assets_dir, release_config)
    target = target_dir / path.name
    if target.exists(): raise ExistingReleaseError(target)

    target.write_text(frontmatter.dumps(compiled), "utf-8")
    path.unlink()  # Remove from draft
    return target
```

### `mono-pub publish <type|all> [--dry-run] [--no-git]`

Publishes released content to the Jekyll site via git.

**Flags:**
| Flag | Effect |
|------|--------|
| `--no-git` | Skip git add/commit/push (only copy files) |
| `--git` | Only run git commands (skip file copy) |
| `--dry-run` | Start a local Jekyll preview server instead of pushing |

**Logic (`commands/publish.py` → `process/publish.py`):**

```python
def publish_type(config, content_type, *, copy_files, run_git, dry_run):
    if copy_files and run_git:
        ensure_publish_git_repo(base_dir)
        ensure_clean_git_status(base_dir)

    if copy_files:
        result = publish_files(...)        # Copy releases + assets
        result.files = published files
        result.asset_dirs = published asset dirs

    if run_git:
        result.git = run_git_publish(base_dir, content_type)
        # git add . → git commit -m "Publish <type>" → git push

    if dry_run:
        result.jekyll = run_jekyll_server(base_dir, port)
        # bundle exec jekyll serve --port <port>

    return result
```

**Error types:**
- `DirtyPublishRepositoryError` — uncommitted changes in publish repo
- `GitCommandError` — git command failure
- `GitRepositoryError` — publish base is not a git repo root
- `JekyllCommandError` — jekyll/bundle command failure

---

## Content Types

| Type | File Extension | Frontmatter | Default Key | Asset Support |
|------|---------------|-------------|-------------|---------------|
| **post** | `*.md` | `layout: post`, `categories`, `tags` | `posts` | images, assets |
| **project** | `*.md` | `layout: post`, `archive_record`, `short_description` | `projects` | images, assets |
| **music** | `*.md` | `layout: post`, `categories: music`, `permalink: /music/{slug}` | `music` | images, assets |

---

## Jinja2 Templates

Three Jinja2 templates live in `templates/` and generate the Jekyll frontmatter for each content type.

### `post.md.j2`

```jinja2
---
layout: post
title: {{ title }}
short_description:
image_preview:
permalink:
archive_record:
date: {{ date }}
author: "{{ author }}"
categories:
tags: []
featured: false
release: false
---
```

### `project.md.j2`

```jinja2
---
layout: post
title: {{ title }}
date: {{ date }}
author: "{{ author }}"
categories:
tags: []
release: false
---
```

### `music.md.j2`

```jinja2
---
layout: post
title: {{ title }}
date: {{ date }}
author: "{{ author }}"
permalink: /music/{{ permalink }}
categories: music
tags: []
release: false
---
```

**Template rendering context:**

```python
template_context = {
    "title": title,
    "date": today.isoformat(),
    "author": config["author"],
    "type": content_type,
    "permalink": slug if content_type == "music" else None,
}
```

---

## Release Process

The release pipeline is implemented across three files:

### 1. `process/release_config.py`

Defines release rules:

```python
DEFAULT_RELEASE_CONFIG = {
    "build_fields": ["release", "validate", "draft_only"],
    "frontmatter_image_fields": ["image_preview"],
    "category_fields": ["categories"],
    "preserve_string_fields": ["title", "short_description"],
    "required_fields": {
        "common": ["title", "date", "author"],
        "project": ["archive_record", "short_description"],
    },
}

PATH_KEYS_BY_TYPE = {
    "post": "posts",
    "project": "projects",
    "music": "music",
}

get_release_config()  # Merges user's config with defaults
```

### 2. `process/validate.py`

Validates required frontmatter fields:

```python
def missing_required_fields(post, release_config, content_type) -> list[str]:
    required = list(required_fields["common"])
    required.extend(required_fields.get(content_type, []))
    return [key for key in required if not has_frontmatter_value(post, key)]
```

### 3. `process/release.py`

Orchestrates the release:

```python
def release_draft(path, target_dir, assets_dir, release_config, content_type):
    post = frontmatter.load(path)
    missing = missing_required_fields(post, release_config, content_type)
    if missing: raise MissingRequiredFieldsError(path, missing)

    compiled = compile_draft(post, path, assets_dir, release_config)
    target = target_dir / path.name
    target.write_text(frontmatter.dumps(compiled))
    path.unlink()  # Remove from draft
```

### 4. `process/compile.py`

Prepares frontmatter for release:

```python
def compile_draft(post, draft_path, assets_dir, release_config):
    remove_build_fields(post, release_config)        # Strip `release`, `validate`, etc.
    normalize_frontmatter(post, release_config)       # Lowercase non-preserved fields
    replacements = consolidate_images(...)           # Consolidate images
    replace_image_path(post, replacements)            # Rewrite image URLs
    return post
```

### 5. `process/assets.py`

Handles image consolidation:

```python
def consolidate_images(post, draft_path, assets_dir, release_config) -> dict[str, str]:
    slug = slugify(post.metadata["title"])
    target_dir = assets_dir / slug

    # Process images in content
    for match in IMAGE_PATTERN.finditer(post.content):
        replacement = consolidate_image(image_path, draft_path, target_dir, slug)
        if replacement: replacements[match.group(0)] = replacement

    # Process images in frontmatter
    for field in frontmatter_image_fields:
        post.metadata[field] = consolidate_image(...)

    return replacements

def consolidate_image(image_path, draft_path, target_dir, slug) -> str | None:
    source = resolve_image_path(image_path, draft_path)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return f"assets/{slug}/{target.name}"
```

Image URLs in markdown and frontmatter are rewritten and replaced with `{{% picture default {{path}} alt="{{alt}}" %}}` (Jekyll picture tag).

---

## Publish Process

The publish pipeline (file copy → git push → Jekyll server) is in `process/publish.py`.

### `PublishResult` dataclass

```python
@dataclass
class PublishResult:
    content_type: str
    files: list[Path]              # Published content files
    asset_dirs: list[Path]         # Published asset directories
    git: GitResult | None = None
    jekyll: JekyllResult | None = None
```

### File copying

`copy_release_files()` copies all `.md` files from releases dir to publish dir.
`copy_referenced_assets()` collects image slugs from content + frontmatter using regex `ASSET_PATH_PATTERN = re.compile(r"assets/([^/\s\"')]+)")`, then copies referenced asset directories.

### Git publishing

```python
def run_git_publish(base_dir, content_type) -> GitResult:
    git add .
    if not git_has_changes():
        return GitResult(committed=False, pushed=False, message="No changes")
    git commit -m "Publish <content_type>"
    git push
    return GitResult(committed=True, pushed=True, message="Publish <content_type>")
```

### Jekyll dry-run

```python
def run_jekyll_server(base_dir, port) -> JekyllResult:
    subprocess.Popen(
        ["bundle", "exec", "jekyll", "serve", "--port", str(port)],
        cwd=base_dir,
    )
    return JekyllResult(base_dir, port)
```

---

## TUI Interface

The TUI is implemented with the Textual framework (optional `tui` extra).

### `tui_interface/app.py` — `MonoPubTuiApp`

```
class MonoPubTuiApp(App):
    __init__():        # Initial setup
    compose():         # Build the UI layout
    on_mount():        # Initial setup on app launch
    on_select_changed():    # Handle content type selection
    compose_output():    # Build output widget
    log_output():    # Display log messages
    action_refresh():    # Refresh file listings
    on_button_pressed():   # Handle button actions
    refresh_summary():     # Update summary
    write_file_group():    # Upload payload via Postman
    create_draft():     # Create new draft via CLI
    open_selected():     # Open selected file in editor
    release_selected():  # Release selected file
    publish_selected():  # Publish selected file
    report_publish_result() # Show publish outcome
    markdown_files():    # List markdown files in current dir
    selected_content_type() # Get current content type selection
```

The TUI provides an interactive terminal interface with:
- Content type selection (post / project / music)
- File listing and navigation
- Actions: Create, Open, Release, Publish
- Live log output
- Publish result reporting

---

## Dependency Overview

### Core Dependencies (`pyproject.toml`)

| Package | Purpose |
|---------|---------|
| `jinja2>=3.1.6` | Template rendering for frontmatter |
| `python-frontmatter>=1.3.0` | YAML frontmatter parsing/serialization |
| `python-slugify>=8.0.4` | URL-safe slug generation |
| `pyyaml>=6.0.3` | YAML config parsing |
| `typer>=0.26.8` | CLI framework |

### Optional TUI Extra

| Package | Purpose |
|---------|---------|
| `textual>=6.6.0` | Terminal GUI framework |

---

*Generated from mono-pub source code as of 2026-08-19.*
