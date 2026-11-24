"""
WCAG AA Contrast Verification Script for SmartMIS Theme Engine.
Calculates relative luminance and contrast ratios according to W3C WCAG 2.1 specifications.
Ensures all text/background pairs meet or exceed the WCAG AA threshold (4.5:1 for normal text, 3.0:1 for large text/UI components).
"""
import sys

def hex_to_rgb(hex_code: str):
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c * 2 for c in hex_code])
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def linearize_channel(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(rgb) -> float:
    r, g, b = [linearize_channel(v) for v in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = relative_luminance(hex_to_rgb(hex1))
    l2 = relative_luminance(hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def run_verification():
    # Defined color pairs across Dark Mode and Light Mode
    checks = [
        # Dark Mode Main App
        ("Dark Mode: Headings on Page Bg", "#FFFFFF", "#071322", 4.5),
        ("Dark Mode: Headings on Card Bg", "#FFFFFF", "#0E2240", 4.5),
        ("Dark Mode: Headings on Elevated Container", "#FFFFFF", "#14305A", 4.5),
        ("Dark Mode: Body Text on Page Bg", "#E6EEF9", "#071322", 4.5),
        ("Dark Mode: Body Text on Card Bg", "#E6EEF9", "#0E2240", 4.5),
        ("Dark Mode: Body Text on Elevated Container", "#E6EEF9", "#14305A", 4.5),
        ("Dark Mode: Muted Text on Page Bg", "#9FB3CC", "#071322", 4.5),
        ("Dark Mode: Muted Text on Card Bg", "#9FB3CC", "#0E2240", 4.5),
        ("Dark Mode: Muted Text on Elevated Container", "#9FB3CC", "#14305A", 4.5),

        # Dark Mode Sidebar & Controls
        ("Dark Mode: Sidebar Text on Sidebar Bg", "#E2E8F0", "#071527", 4.5),
        ("Dark Mode: Sidebar Nav Active Text", "#FFFFFF", "#0B1F3A", 4.5),
        ("Dark Mode: Sidebar Expander Text", "#E6EEF9", "#14305A", 4.5),
        ("Dark Mode: Tooltip Text on Bg", "#FFFFFF", "#0B1F3A", 4.5),
        ("Dark Mode: Primary Button (Bold/Large UI)", "#FFFFFF", "#EA580C", 3.0),

        # Light Mode Main App
        ("Light Mode: Headings on Page Bg", "#0B1F3A", "#F4F8FF", 4.5),
        ("Light Mode: Headings on Card Bg", "#0B1F3A", "#FFFFFF", 4.5),
        ("Light Mode: Body Text on Page Bg", "#1E293B", "#F4F8FF", 4.5),
        ("Light Mode: Body Text on Card Bg", "#1E293B", "#FFFFFF", 4.5),
        ("Light Mode: Muted Text on Page Bg", "#475569", "#F4F8FF", 4.5),
        ("Light Mode: Muted Text on Card Bg", "#475569", "#FFFFFF", 4.5),
        ("Light Mode: Primary Button (Bold/Large UI)", "#FFFFFF", "#EA580C", 3.0),
    ]

    print("=" * 80)
    print("  SmartMIS WCAG 2.1 AA Contrast Ratio Verification Suite")
    print("=" * 80)
    print(f"{'UI Element / Pair':<44} | {'FG':<8} | {'BG':<8} | {'Ratio':<7} | {'Required':<8} | {'Status'}")
    print("-" * 80)

    failed = 0
    for name, fg, bg, min_ratio in checks:
        ratio = contrast_ratio(fg, bg)
        passed = ratio >= min_ratio
        status = "PASSED" if passed else "FAILED"
        if not passed:
            failed += 1
        print(f"{name:<44} | {fg:<8} | {bg:<8} | {ratio:>5.2f}:1 | {min_ratio:>5.1f}:1  | {status}")

    print("-" * 80)
    if failed == 0:
        print(f"SUCCESS: All {len(checks)} color combinations meet or exceed WCAG AA standards!\n")
        return 0
    else:
        print(f"ERROR: {failed} color combination(s) failed WCAG AA requirements.\n")
        return 1

if __name__ == "__main__":
    sys.exit(run_verification())
