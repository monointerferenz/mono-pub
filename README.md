# mono-pub

mono-pub is a tool for publishing content at monointerferenz.
It offers a command line interface and an optional terminal-based GUI.

It prepares content to be published via Jekyll.

## Installation

### Requirements

- Python 3.13 or newer
- uv installed

### Clone

```bash
git clone <repository-url>
cd mono-pub
```

### Setup the environment

Install all dependencies including the optional TUI:

```bash
uv sync --all-extras
```

## Usage

### Development

Run the tool directly with `uv`:

```bash
uv run mono-pub --help
```

Example — create a draft post:

```bash
uv run mono-pub new post "My first post"
```

### Install globally (optional)

```bash
uv tool install -e ".[tui]"
```

**Then it can be called with:**

```bash
mono-pub --help
mono-pub tui
```

### Update

After pulling changes from the repository:

```bash
git pull
uv sync --all-extras
```

If the tool was installed globally and metadata has changed (entry points, dependencies, etc.):

```bash
uv tool install -e ".[tui]" --reinstall
```

## Commands

### Create new content

The tool offers three types of content:

- **posts** — all-purpose articles
- **projects** — artworks to be presented in an online portfolio
- **music** — a special type of project

```bash
mono-pub new post "My first post"
mono-pub new project "My first project"
mono-pub new music "My first music"
```

### List

```bash
mono-pub list draft          # List all draft posts, projects, music
mono-pub list draft post     # List only draft posts
mono-pub list release        # List all released content
mono-pub list release post   # List only released posts
```

### Open

Opens the draft folder in the configured editor (set `editor_command` in config):

```bash
mono-pub open post
mono-pub open project
mono-pub open music
```

### Release

Drafts marked `release: true` in the frontmatter can be released. They will be verified, paths and links will be set for deployment, assets will be copied to the assets folder, and frontmatter will be stripped down.

```bash
mono-pub release post
mono-pub release project
mono-pub release music
mono-pub release all
```

### Publish

Publishes released content to the Jekyll server via git.

```bash
mono-pub publish post
mono-pub publish project
mono-pub publish music
mono-pub publish all
```

Flags:

| Flag | Description |
| --- | --- |
| `--no-git` | Skip git add / commit / push |
| `--git` | Only run git add / commit / push (skip file copy) |
| `--dry-run` | Simulate the publish process through a local Jekyll server |

Example:

```bash
mono-pub publish post --dry-run
mono-pub publish all --no-git
```

### TUI

Launches the terminal-based interface:

```bash
mono-pub tui
```
