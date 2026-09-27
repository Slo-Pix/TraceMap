"""TraceMap palette. One place to change the whole skin.

Mirrors CodeMap's tonal range so the two tools read as one family, but swaps the
accent from green to amber: green and red are reserved for test outcomes, and a
green chrome would collide with the fail-before/pass-after proof.
"""

BG = "#0e0e0e"          # app background
PANEL = "#141414"       # panel background
HOVER = "#1f1f1f"       # row hover
BORDER = "#3c3c3c"      # resting border
ACCENT = "#e8a33d"      # amber: focus, cursors, active stage
ACCENT_DIM = "#a8762c"  # selected tree guides, subdued accent
TEXT = "#d4d4d4"        # body text
TITLE = "#e6e6e6"       # panel titles
MUTED = "#7d7d7d"       # hints, subtitles, "not in index"
PASS = "#7fd08a"        # test passed / after
FAIL = "#e06c6c"        # test failed / before / crash frame
WARN = "#e6d690"        # changed, partial
INFO = "#8fd0e6"        # callers/callees, metadata

# Pipeline stage glyphs, paired with the colour each should render in.
GLYPH_PENDING = ("·", MUTED)
GLYPH_RUNNING = ("◐", ACCENT)
GLYPH_DONE = ("✓", PASS)
GLYPH_FAILED = ("✗", FAIL)
