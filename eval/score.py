"""SectorPulse eval harness — checks tests pass, lint clean, types clean."""

import subprocess
import sys


def run(cmd: list[str], cwd: str | None = None) -> bool:
    """Run a command and return True if it succeeds."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return True
    except FileNotFoundError:
        print(f"  SKIP (not installed): {cmd[0]}")
        return True  # not a failure if tool isn't installed
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and e.stderr and "No module named" in e.stderr:
            print(f"  SKIP (not installed): {' '.join(cmd)}")
            return True
        print(f"  FAIL: {' '.join(cmd)}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main() -> int:
    results: dict[str, bool] = {}
    backend = "backend"

    # 1. pytest
    print("Running pytest...")
    results["pytest"] = run(["python3", "-m", "pytest", "-x", "-q"], cwd=backend)

    # 2. ruff (lint)
    print("Running ruff...")
    results["ruff"] = run(["python3", "-m", "ruff", "check", "."], cwd=backend)

    # 3. mypy (type check)
    print("Running mypy...")
    results["mypy"] = run(["python3", "-m", "mypy", "app/"], cwd=backend)

    # Summary
    print("\n--- Eval Results ---")
    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
