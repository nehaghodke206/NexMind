import sys
from pathlib import Path

# Ensure package directory is in sys.path
package_root = Path(__file__).resolve().parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from dependency_guardian.cli import main

if __name__ == "__main__":
    main()

