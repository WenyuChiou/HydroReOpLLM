"""Resume only the user-authorized 551-day suffix; never replay earlier days."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from delaware_operations.anik_recovery import main

if __name__ == "__main__":
    main()
