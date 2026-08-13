"""Render all pages of a PDF to PNG files for deterministic visual QA."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def render(pdf_path: Path, output_dir: Path, dpi: int = 180) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    outputs: list[Path] = []
    for index, page in enumerate(document):
        output = output_dir / f"page-{index + 1:02d}.png"
        page.get_pixmap(matrix=matrix, alpha=False).save(output)
        outputs.append(output)
    document.close()
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()
    for output in render(args.pdf, args.output, args.dpi):
        print(output)


if __name__ == "__main__":
    main()
