"""Build the committed OFL CJK font subset from a downloaded source font.

Usage (development-only):
    python prepare_font_subset.py --source NotoSansSC-source.ttf

Reads every corpus Markdown file to derive the exact character set, instances
the variable font to weight 400, subsets to those characters, and writes the
small subset TTF under ``fixtures/fonts/NotoSansSC-Subset.ttf``. Fails loudly
if any corpus character has no glyph.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

from tests.evaluation.datasets import paths


def corpus_charset(corpus_dir: Path) -> set[str]:
    chars: set[str] = set()
    for path in corpus_dir.glob("*.md"):
        chars.update(path.read_text(encoding="utf-8"))
    chars.update(chr(code) for code in range(0x20, 0x7F))
    chars.update({"\u00d7"})  # multiplication sign
    chars = {
        char for char in chars
        if ord(char) >= 0x20 and ord(char) != 0x7F
    }
    return chars


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="source variable TTF")
    parser.add_argument(
        "--dataset",
        default=paths.active_dataset_name(),
        help="evaluation dataset directory name",
    )
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    output = Path(args.output) if args.output else (
        paths.fonts_dir(args.dataset) / "NotoSansSC-Subset.ttf"
    )

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"source font not found: {source_path}", file=sys.stderr)
        return 2

    varfont = TTFont(str(source_path))
    static = instantiateVariableFont(varfont, {"wght": 400}, inplace=False)
    varfont.close()

    chars = corpus_charset(paths.corpus_dir(args.dataset))
    options = subset.Options()
    options.hinting = False
    sub = subset.Subsetter(options)
    sub.populate(unicodes=sorted(ord(char) for char in chars))
    sub.subset(static)

    cmap = static.getBestCmap()
    missing = sorted(ord(char) for char in chars if ord(char) not in cmap)
    if missing:
        sample = ", ".join(f"U+{code:04X}" for code in missing[:40])
        print(f"{len(missing)} characters missing glyphs: {sample}", file=sys.stderr)
        return 3

    output.parent.mkdir(parents=True, exist_ok=True)
    static.save(str(output))
    static.close()
    print(f"subset written: {output} ({output.stat().st_size} bytes, "
          f"{len(chars)} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
