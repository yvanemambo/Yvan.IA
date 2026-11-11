"""Configuration pytest pour rendre la racine du dépôt importable."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_string = str(ROOT)
if root_string not in sys.path:
    sys.path.insert(0, root_string)
