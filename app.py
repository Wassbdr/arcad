"""PREDI-Care application launcher."""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from predi_care.app_v2 import main

if __name__ == "__main__":
    main()
