#!/usr/bin/env python3
"""
Generate backend module index with Mermaid dependency graph and file inventory.
Auto-generated from AST analysis of cs2tracker/*.py.

Run from backend/ directory:
  python tools/build_index.py                           # print to stdout
  python tools/build_index.py PROJECT_INDEX.md          # write to file
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path


def extract_ast_info(file_path: Path) -> tuple[list[str], set[str], str, int]:
    """Extract symbols, imports, docstring, and line count from a Python file."""
    try:
        text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError):
        return [], set(), "", 0

    symbols = []
    imports = set()
    docstring = ast.get_docstring(tree) or ""
    lines = len(text.splitlines())
    all_names_set = set()

    # Find __all__ for re-export detection (e.g., db/__init__.py)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                all_names_set.add(elt.value)

    # Collect exports (top-level only)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_") or node.name in all_names_set:
                symbols.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Include if UPPERCASE (constant) or in __all__
                    if target.id.isupper() or target.id in all_names_set:
                        symbols.append(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                if node.target.id.isupper() or node.target.id in all_names_set:
                    symbols.append(node.target.id)

    # Collect all imports (including conditional ones, hence ast.walk)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                imports.add(module)

    return symbols[:15], imports, docstring, lines  # Cap to 15 exports


def resolve_local_imports(imports: set[str], cs2tracker_root: Path) -> set[str]:
    """
    Resolve which imports are local to cs2tracker.
    Returns paths to actual imported modules (e.g., "cs2tracker.domain.stats").
    """
    local = []
    for imp in sorted(imports):
        if imp.startswith("cs2tracker"):
            local.append(imp)
    return set(local[:10])  # Cap to 10 imports


def get_bucket(relative_path: Path) -> str:
    """Determine the bucket (module level) for a file."""
    parts = relative_path.parts
    if len(parts) == 1:
        return "root"
    return parts[0]


def build_backend_index(output_path: str | None = None):
    """Main: walk cs2tracker/, extract AST, generate Markdown."""

    # Resolve paths robustly
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent
    cs2tracker_dir = backend_dir / "cs2tracker"

    if not cs2tracker_dir.exists():
        print(f"Error: {cs2tracker_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Collect all .py files
    py_files = sorted(f for f in cs2tracker_dir.rglob("*.py") if "__pycache__" not in f.parts)

    if not py_files:
        print(f"No .py files found in {cs2tracker_dir}", file=sys.stderr)
        sys.exit(1)

    # Parse each file
    file_data: dict[Path, tuple[list[str], set[str], str, int, str]] = {}
    bucket_files: dict[str, list[Path]] = defaultdict(list)
    bucket_edges: dict[tuple[str, str], int] = defaultdict(int)

    for py_file in py_files:
        # Skip empty __init__.py files
        if py_file.name == "__init__.py":
            if py_file.read_text(encoding="utf-8").strip() == "":
                continue

        rel_path = py_file.relative_to(cs2tracker_dir)
        symbols, imports, docstring, lines = extract_ast_info(py_file)

        bucket = get_bucket(rel_path)
        file_data[py_file] = (symbols, imports, docstring, lines, bucket)
        bucket_files[bucket].append(py_file)

        # Build edges: src_bucket -> dst_bucket
        local_imports = resolve_local_imports(imports, cs2tracker_dir)
        for imp in local_imports:
            # Extract dst bucket from import like "cs2tracker.domain.stats"
            parts = imp.split(".")
            if len(parts) >= 3:
                dst_bucket = parts[1]  # e.g., "domain"
                if dst_bucket != bucket and dst_bucket != "":
                    bucket_edges[(bucket, dst_bucket)] += 1

    # Build Mermaid graph
    all_buckets = sorted(bucket_files.keys())
    mermaid_lines = ["graph LR"]

    # Add nodes with file counts
    for bucket in all_buckets:
        file_count = len(bucket_files[bucket])
        mermaid_lines.append(f'    {bucket}["{bucket}/\\n{file_count} files"]')

    # Add edges with counts
    for (src, dst), count in sorted(bucket_edges.items()):
        mermaid_lines.append(f"    {src} -->|{count}| {dst}")

    # Build per-bucket file tables
    output_lines = [
        "<!-- AUTO-GENERATED by `python tools/build_index.py`. DO NOT EDIT. -->",
        "",
        "# Backend Index — cs2tracker",
        "",
        f"{len(py_files)} files · {sum(f[3] for f in file_data.values())} lines",
        "",
        "## Module Graph",
        "",
        "```mermaid",
        *mermaid_lines,
        "```",
        "",
    ]

    # Summary table
    output_lines.extend(
        [
            "## Summary by Module",
            "",
            "| Module | Files | Lines | Description |",
            "|---|---|---|---|",
        ]
    )
    for bucket in all_buckets:
        files = bucket_files[bucket]
        total_lines = sum(file_data[f][3] for f in files)
        if bucket == "domain":
            desc = "Pure business logic (no project dependencies)"
        elif bucket == "infra":
            desc = "External integrations (parser, sources, etc.)"
        elif bucket == "db":
            desc = "SQLAlchemy models and session"
        elif bucket == "api":
            desc = "FastAPI routes and schemas"
        else:
            desc = ""
        output_lines.append(f"| `{bucket}/` | {len(files)} | {total_lines} | {desc} |")

    # Per-bucket file tables
    for bucket in all_buckets:
        output_lines.extend(
            [
                "",
                f"## {bucket}/",
                "",
                "| File | Lines | Exports | Imports |",
                "|---|---|---|---|",
            ]
        )

        for py_file in sorted(bucket_files[bucket]):
            symbols, imports, docstring, lines, _ = file_data[py_file]
            rel_path = py_file.relative_to(cs2tracker_dir)

            symbol_str = ", ".join(symbols) + ("…" if len(symbols) == 15 else "")
            symbol_str = symbol_str or "—"

            import_str = ", ".join(sorted(list(resolve_local_imports(imports, cs2tracker_dir)))[:3])
            import_str = import_str or "—"

            output_lines.append(f"| `{rel_path}` | {lines} | {symbol_str} | {import_str} |")

    output_text = "\n".join(output_lines)

    if output_path:
        Path(output_path).write_text(output_text, encoding="utf-8")
        print(f"Indexed {len(py_files)} files. Wrote {output_path} ({len(output_text)} bytes).")
    else:
        print(output_text)


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else None
    build_backend_index(output_path)
