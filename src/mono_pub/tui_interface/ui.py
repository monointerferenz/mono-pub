import dataclasses
from importlib.resources import files

from rich.console import Console
from textual.theme import BUILTIN_THEMES

# Path to the CSS file
CSS_PATH = files("mono_pub.assets").joinpath("styles.tcss")

# Custom Textual theme, based on the built-in "textual-dark" theme with a
# minimal set of overrides for a near-black, neutral grayscale palette
# (inspired by Vercel/shadcn-ui), keeping vibrant color reserved for
# semantic states (focus, selection, errors, warnings, success).
# =============================================================================
# Common dark background foundation for all themes
# =============================================================================
DARK_FOUNDATION = {
    "background": "#1E2021",  # Near black
    "surface": "#282828",     # Slightly elevated
    "panel": "#45525A",       # Cool blue-gray
    "foreground": "#E8DCB6",  # Warm off-white
}

# =============================================================================
# Theme 1: "mono Rosa" - Elegant Pink/Purple
# Subtle, sophisticated, creative feel
# =============================================================================
THEME_ROSA = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
    name="mono-rosa",
    primary="#DCCC92",       # Soft gold
    secondary="#908376",     # Warm gray
    accent="#C8899B",        # Muted pink-purple
    **DARK_FOUNDATION
)

# =============================================================================
# Theme 2: "mono Teal" - Calm & Natural
# Professional yet relaxed, great for productivity
# =============================================================================
THEME_TEAL = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
    name="mono-teal",
    primary="#86A382",       # Muted sage green
    secondary="#708584",     # Cool gray
    accent="#8AA499",        # Teal-green
    **DARK_FOUNDATION
)

# =============================================================================
# Theme 3: "mono Ember" - Warm & Energetic
# Inviting, creative, attention-grabbing
# =============================================================================
THEME_EMBER = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
    name="mono-ember",
    primary="#E85741",       # Warm red-orange
    secondary="#C7642A",     # Deep orange
    accent="#DA8F5A",        # Coral orange
    **DARK_FOUNDATION
)

# =============================================================================
# Theme 4: "mono Ocean" - Clean & Professional
# Trustworthy, organized, good for data/code work
# =============================================================================
THEME_OCEAN = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
    name="mono-ocean",
    primary="#6298B7",       # Ocean blue
    secondary="#548386",     # Steel teal
    accent="#8AA191",        # Water blue-green
    **DARK_FOUNDATION
)

# =============================================================================
# Theme 5: "mono Gold" - Luxe & Refined
# Premium feel, warm accents, sophisticated
# =============================================================================
THEME_GOLD = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
    name="mono-gold",
    primary="#F1BF4F",       # Rich gold
    secondary="#BC615E",     # Terracotta
    accent="#D88C59",        # Copper orange
    **DARK_FOUNDATION
)

# =============================================================================
# Theme 5: "mono Black" - Black
# Black
# =============================================================================
THEME_BLACK = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
    name="mono-black",
    primary="#e4e4e7",
    secondary="#52525b",
    accent="#e4e4e7",
    foreground="#fafafa",
    background="#0a0a0a",
    surface="#111113",
    panel="#18181b",
    # **DARK_FOUNDATION
)

THEME_MONO_BASE = dataclasses.replace(
    BUILTIN_THEMES["textual-dark"],
	name="monobase",

	primary="#E8DCB6",
	accent="#DCCC92",

	background="#282828FF",
	foreground="#bfbfac",

	surface="#1E2021",
	panel="#908376",

	success="#A5A53CFF",
	warning="#C7642AFF",
	error="#E85741FF",
	dark=True,
	variables={},
    # **DARK_FOUNDATION #4a6c6e
)

# =============================================================================
# Export all themes as dictionary for easy selection
# =============================================================================
MONO_THEMES = {
    "rosa": THEME_ROSA,
    "teal": THEME_TEAL,
    "ember": THEME_EMBER,
    "ocean": THEME_OCEAN,
    "gold": THEME_GOLD,
    "black": THEME_BLACK,
    "monobase": THEME_MONO_BASE,
}

# Default to Rosa (most versatile)
THEME = THEME_TEAL

# To use a different theme, simply change:
# THEME = MONO_THEMES["ocean"]

# Rich console
CONSOLE = Console()
