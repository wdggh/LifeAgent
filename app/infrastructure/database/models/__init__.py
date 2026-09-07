"""Auto-import every ORM model module so tables register on Base.metadata."""

from importlib import import_module
from pathlib import Path

for _module in Path(__file__).parent.glob("*.py"):
    if _module.name.startswith("_"):
        continue
    import_module(f"{__name__}.{_module.stem}")
