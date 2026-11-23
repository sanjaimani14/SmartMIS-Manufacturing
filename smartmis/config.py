"""SmartMIS settings."""
REJECTION_TARGET = 4.0      # % - green at/below, amber up to target*1.5, red above
AMBER_LIMIT = REJECTION_TARGET * 1.5
REPORT_DIR = "reports"
WEEKLY_CRON = {"day_of_week": "mon", "hour": 7}
MONTHLY_CRON = {"day": 1, "hour": 7}
COMPANY = "SmartMIS Manufacturing"
