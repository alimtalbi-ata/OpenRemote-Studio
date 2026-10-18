from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()
assert VERSION and VERSION.count(".")==1
print(VERSION)
