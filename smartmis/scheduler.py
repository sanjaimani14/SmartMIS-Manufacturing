"""
Scheduler and automation engine for SmartMIS.
Manages dynamic cron schedules, automated report execution with retries,
run history tracking, and report archive management.
"""
import io
import json
import logging
import os
import time
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

try:
    import config
    from reports import (
        get_template,
        list_templates,
        prepare_template_report,
        send_report_email,
        to_excel_from_template,
        to_pdf_from_template,
    )
except ImportError:
    try:
        from smartmis import config
        from smartmis.reports import (
            get_template,
            list_templates,
            prepare_template_report,
            send_report_email,
            to_excel_from_template,
            to_pdf_from_template,
        )
    except ImportError:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import config
        from reports import (
            get_template,
            list_templates,
            prepare_template_report,
            send_report_email,
            to_excel_from_template,
            to_pdf_from_template,
        )

log = logging.getLogger("smartmis.scheduler")

# ==============================================================================
# 1. SCHEDULE CONFIGURATION PERSISTENCE
# ==============================================================================

def load_schedule_config() -> Dict[str, Any]:
    """Load schedule parameters from persistent JSON configuration."""
    cfg_file = config.SCHEDULE_CONFIG_FILE
    defaults = {
        "weekly": dict(config.WEEKLY_CRON),
        "monthly": dict(config.MONTHLY_CRON),
        "email_enabled": True,
        "email_dry_run": config.SMTP_DRY_RUN,
        "recipients": config.SMTP_TO,
    }
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                defaults.update(user_cfg)
        except Exception as e:
            log.warning("Could not read schedule config %s: %s", cfg_file, e)
    return defaults


def save_schedule_config(cfg: Dict[str, Any]) -> None:
    """Save schedule configuration to persistent JSON file."""
    cfg_file = config.SCHEDULE_CONFIG_FILE
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ==============================================================================
# 2. DYNAMIC SCHEDULER CONTROLLER
# ==============================================================================

def update_scheduler_job(
    scheduler: BackgroundScheduler,
    job_id: str,
    cron_kwargs: Dict[str, Any],
    get_df_func: Callable[[], pd.DataFrame],
) -> None:
    """Reschedule or register an automated job dynamically."""
    trigger = CronTrigger(**cron_kwargs)
    job = scheduler.get_job(job_id)
    if job:
        job.reschedule(trigger)
        log.info("Rescheduled job '%s' with trigger: %s", job_id, trigger)
    else:
        scheduler.add_job(
            lambda: run_scheduled_automation(get_df_func()),
            trigger=trigger,
            id=job_id,
        )
        log.info("Added new scheduled job '%s' with trigger: %s", job_id, trigger)


# ==============================================================================
# 3. AUTOMATED EXECUTION WITH TIMING, RETRY & HISTORY
# ==============================================================================

def run_scheduled_automation(
    df: pd.DataFrame,
    outdir: Optional[str] = None,
    send_email: bool = True,
    max_retries: int = 2,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Execute all registered templates, generate Excel and PDF deliverables,
    attempt email dispatch, handle retries on transient errors, and log audit history.
    """
    start_time = time.time()
    dest_dir = outdir or config.REPORT_DIR
    os.makedirs(dest_dir, exist_ok=True)
    today_stamp = date.today().isoformat()

    templates = list_templates()
    if not templates:
        # Fallback to standard 3 templates if not loaded
        log.warning("No templates loaded via discovery; checking default IDs")
        for tid in ["weekly_foundry", "weekly_machine_shop", "monthly_rejection"]:
            t = get_template(tid)
            if t:
                templates[tid] = t

    generated_files: List[str] = []
    errors: List[str] = []
    combined_commentaries: List[str] = []

    for template_id, template in templates.items():
        # Retry loop per report deliverable
        success = False
        attempt = 0
        last_error = ""

        while attempt <= max_retries and not success:
            try:
                sections, title, kpis_map, commentary, t_dict = prepare_template_report(df, template)
                combined_commentaries.append(f"[{template.get('title', template_id)}]:\n{commentary}")

                # Export Excel
                xlsx_bytes = to_excel_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=t_dict)
                xlsx_path = os.path.join(dest_dir, f"{template_id}_{today_stamp}.xlsx")
                with open(xlsx_path, "wb") as f:
                    f.write(xlsx_bytes)
                generated_files.append(xlsx_path)

                # Export PDF
                pdf_bytes = to_pdf_from_template(sections, title, kpi_dict=kpis_map, commentary=commentary, template=t_dict)
                pdf_path = os.path.join(dest_dir, f"{template_id}_{today_stamp}.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                generated_files.append(pdf_path)

                success = True
            except Exception as e:
                attempt += 1
                last_error = str(e)
                log.warning("Attempt %d failed for template %s: %s", attempt, template_id, e)
                if attempt <= max_retries:
                    time.sleep(0.5)

        if not success:
            errors.append(f"{template_id}: {last_error}")

    duration = round(time.time() - start_time, 2)
    overall_status = "SUCCESS" if not errors else ("PARTIAL_SUCCESS" if generated_files else "FAILED")

    # Email delivery
    email_status = "Skipped"
    if send_email and generated_files:
        cfg = load_schedule_config()
        if cfg.get("email_enabled", True):
            ok_email, email_msg = send_report_email(
                generated_files,
                recipients=cfg.get("recipients"),
                commentary="\n\n".join(combined_commentaries[:2]),
                dry_run=cfg.get("email_dry_run", config.SMTP_DRY_RUN),
            )
            email_status = email_msg

    # Log into history.json
    hist_file = os.path.join(dest_dir, "history.json")
    history_entries = []
    if os.path.exists(hist_file):
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                history_entries = json.load(f)
        except Exception:
            history_entries = []

    log_entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": overall_status,
        "duration_sec": duration,
        "files_count": len(generated_files),
        "files": [os.path.basename(f) for f in generated_files],
        "email_delivery": email_status,
        "errors": errors if errors else None,
    }
    history_entries.append(log_entry)
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(history_entries[-50:], f, indent=2)

    return generated_files, log_entry


# ==============================================================================
# 4. REPORT ARCHIVE BROWSER
# ==============================================================================

def list_archived_reports(report_dir: Optional[str] = None) -> pd.DataFrame:
    """Scan and list all generated report files in the archive directory."""
    rdir = report_dir or config.REPORT_DIR
    if not os.path.exists(rdir):
        return pd.DataFrame()

    items: List[Dict[str, Any]] = []
    for fname in os.listdir(rdir):
        if fname.endswith((".xlsx", ".pdf")):
            fpath = os.path.join(rdir, fname)
            stat = os.stat(fpath)
            # Infer report type
            lower = fname.lower()
            if "weekly_foundry" in lower:
                rpt_type = "Weekly Foundry"
            elif "weekly_machine_shop" in lower:
                rpt_type = "Weekly Machine Shop"
            elif "monthly_rejection" in lower:
                rpt_type = "Monthly Rejection"
            else:
                rpt_type = "Custom Template"

            items.append({
                "Filename": fname,
                "Report Type": rpt_type,
                "Format": "Excel (.xlsx)" if fname.endswith(".xlsx") else "PDF (.pdf)",
                "Size (KB)": round(stat.st_size / 1024.0, 1),
                "Generated At": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "Path": fpath,
            })

    df = pd.DataFrame(items)
    if not df.empty:
        df = df.sort_values("Generated At", ascending=False).reset_index(drop=True)
    return df
