"""Read-only architecture inventory for OpenRemote Studio.

Reports source modules, size, import dependencies, AST complexity proxies, and
high-level hotspots. Never rewrites source files or imports application modules.
Author: Abdelhalim Talbi.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from pathlib import Path


def inspect_module(path: Path, root: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(raw, filename=str(path))
    imports = set()
    classes = functions = branches = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.ClassDef):
            classes += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
        elif isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match)):
            branches += 1
    return {
        "path": path.relative_to(root).as_posix(),
        "lines": len(raw.splitlines()),
        "bytes": len(path.read_bytes()),
        "classes": classes,
        "functions": functions,
        "branch_nodes": branches,
        "imports": sorted(imports),
    }


def inventory(root: Path) -> dict:
    app = root / "Application"
    if not app.is_dir():
        raise FileNotFoundError("Application directory not found")
    modules = []
    failures = []
    for path in sorted(app.rglob("*.py")):
        if any(part in {".venv", ".venv-build", "build", "dist", "__pycache__"} for part in path.relative_to(app).parts):
            continue
        try:
            modules.append(inspect_module(path, root))
        except (SyntaxError, UnicodeError, OSError) as exc:
            failures.append({"path": path.relative_to(root).as_posix(), "error": str(exc)})
    local_names = {Path(m["path"]).stem for m in modules}
    referenced = Counter(name for m in modules for name in m["imports"] if name in local_names)
    hotspots = sorted(modules, key=lambda m: (-m["lines"], -m["branch_nodes"], m["path"]))[:20]
    return {
        "schema": "openremote.architecture.inventory.v1",
        "module_count": len(modules),
        "total_lines": sum(m["lines"] for m in modules),
        "parse_errors": failures,
        "hotspots": [{k: v for k, v in m.items() if k != "imports"} for m in hotspots],
        "most_imported_local_modules": referenced.most_common(20),
        "modules": modules,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()
    report = inventory(args.root.resolve())
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded)
    return 1 if report["parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
