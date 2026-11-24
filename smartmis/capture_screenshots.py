"""
Automated Playwright Screenshot Capture Script for SmartMIS Views.
"""
import os
import subprocess
import sys
import time
import requests
from playwright.sync_api import sync_playwright

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(CURRENT_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
PORT = 8505
URL = f"http://localhost:{PORT}"

def wait_for_server(url: str, timeout: int = 25) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{url}/_stcore/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def run_capture():
    print(f"Starting Streamlit subprocess on port {PORT}...")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "app.py",
            f"--server.port={PORT}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ],
        cwd=CURRENT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        print("Waiting for Streamlit server to be healthy...")
        if not wait_for_server(URL):
            print("ERROR: Streamlit failed to start within timeout.")
            return

        print("Streamlit is up! Launching Playwright Chromium...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            resolutions = [
                ({"width": 1440, "height": 900}, "1440x900", True),
                ({"width": 1366, "height": 768}, "1366x768", False),
            ]

            pages_to_capture = [
                ("🏠 Home & Overview", "1_home_and_overview.png"),
                ("📊 Executive Dashboard", "2_executive_dashboard.png"),
                ("⚡ Live Shopfloor Stream & Defect Spike", "3_live_defect_spike.png"),
                ("📈 Quality Control & SPC", "4_quality_control_spc.png"),
                ("💰 Cost of Poor Quality (COPQ)", "5_cost_of_poor_quality.png"),
                ("🔮 14-Day Forecasting", "6_14day_forecasting.png"),
                ("🔍 Root-Cause Drill-Down", "7_root_cause_drilldown.png"),
                ("📑 Formal Reports", "8_formal_mis_reports.png"),
                ("⏱️ Time Saved & ROI Counter", "9_time_saved_roi.png"),
                ("✅ Requirements Checklist", "10_requirement_checklist.png"),
                ("💬 Ask Your Data", "11_ask_your_data.png"),
                ("📊 Power BI Integration", "12_power_bi_integration.png"),
            ]

            for vp, res_name, is_default in resolutions:
                print(f"\n--- Capturing suite at resolution: {res_name} ({vp['width']}x{vp['height']}) ---")
                res_dir = os.path.join(SCREENSHOTS_DIR, res_name)
                os.makedirs(res_dir, exist_ok=True)

                context = browser.new_context(viewport=vp)
                page = context.new_page()

                # 1. Open app
                page.goto(URL, wait_until="networkidle")
                time.sleep(3)

                # Check if login screen is presented
                login_user = page.locator('input[aria-label="Username"]')
                if login_user.count() > 0:
                    print("Logging in as admin...")
                    login_user.fill("admin")
                    page.locator('input[aria-label="Password"]').fill("admin123")
                    page.locator('button:has-text("🔐 Secure Enterprise Login")').click()
                    time.sleep(3)
                    page.wait_for_load_state("networkidle")

                for mode in ["light", "dark"]:
                    print(f"\n--- Setting Mode: {mode.upper()} ({res_name}) ---")
                    toggle_input = page.locator('input[aria-label="🌙 Dark Control Room"]')
                    if toggle_input.count() > 0:
                        is_dark = toggle_input.is_checked()
                        if mode == "dark" and not is_dark:
                            page.locator('label:has-text("🌙 Dark Control Room")').click()
                            time.sleep(2.5)
                            page.wait_for_load_state("networkidle")
                        elif mode == "light" and is_dark:
                            page.locator('label:has-text("🌙 Dark Control Room")').click()
                            time.sleep(2.5)
                            page.wait_for_load_state("networkidle")

                    for label, base_fname in pages_to_capture:
                        fname = f"{mode}_{base_fname}"
                        print(f"[{res_name} | {mode}] Navigating to '{label}'...")
                        target = page.locator(f'label:has-text("{label}")')
                        if target.count() > 0:
                            target.click()
                            time.sleep(2.5)
                            page.wait_for_load_state("networkidle")
                        
                        # Capture in resolution subfolder
                        out_path = os.path.join(res_dir, fname)
                        page.screenshot(path=out_path, full_page=False)
                        print(f"Captured: {out_path}")

                        # Also store in base SCREENSHOTS_DIR if default resolution
                        if is_default:
                            base_out = os.path.join(SCREENSHOTS_DIR, fname)
                            page.screenshot(path=base_out, full_page=False)

                context.close()

            browser.close()
            print("\nALL PLAYWRIGHT SCREENSHOTS (1440x900 & 1366x768) CAPTURED SUCCESSFULLY!")
    finally:
        print("Terminating Streamlit process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    run_capture()
