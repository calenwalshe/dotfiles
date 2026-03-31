"""Verify all tracker dependencies import correctly in claude-stack-env."""
import sys


def verify():
    results = []

    checks = [
        ("ultralytics", "import ultralytics; print(ultralytics.__version__)"),
        ("easyocr", "import easyocr"),
        ("torchreid", "import torchreid"),
        ("cv2", "import cv2; print(cv2.__version__)"),
        ("torch", "import torch; print(torch.__version__)"),
        ("numpy", "import numpy; print(numpy.__version__)"),
        ("tqdm", "import tqdm"),
    ]

    all_passed = True
    for name, code in checks:
        try:
            exec(code)
            results.append(f"  PASS  {name}")
        except Exception as e:
            results.append(f"  FAIL  {name}: {e}")
            all_passed = False

    print("\n=== Tracker Import Verification ===")
    for r in results:
        print(r)
    print()

    if all_passed:
        print("All imports OK.")
    else:
        print("Some imports FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    verify()
