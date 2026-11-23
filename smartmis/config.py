"""SmartMIS settings and environment configurations."""
import os

REJECTION_TARGET = 4.0      # % - green at/below, amber up to target*1.5, red above
AMBER_LIMIT = REJECTION_TARGET * 1.5
REPORT_DIR = os.getenv("SMARTMIS_REPORT_DIR", "reports")
TEMPLATE_DIR = os.getenv("SMARTMIS_TEMPLATE_DIR", os.path.join(REPORT_DIR, "templates"))
SCHEDULE_CONFIG_FILE = os.getenv("SCHEDULE_CONFIG_FILE", "schedule_config.json")

WEEKLY_CRON = {"day_of_week": "mon", "hour": 7}
MONTHLY_CRON = {"day": 1, "hour": 7}
COMPANY = "SmartMIS Manufacturing"

# Central database configuration
DB_PATH = os.getenv("SMARTMIS_DB_PATH", "smartmis.db")
SETTINGS_FILE = os.getenv("SMARTMIS_SETTINGS_FILE", "enterprise_settings.json")
USERS_FILE = os.getenv("SMARTMIS_USERS_FILE", "users.json")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# External PMS connection settings
PMS_DATABASE_URL = os.getenv("PMS_DATABASE_URL", "sqlite:///pms_external.db")
MOCK_PMS_URL = os.getenv("MOCK_PMS_URL", "http://127.0.0.1:8001")
COLUMN_MAPPINGS_FILE = os.getenv("COLUMN_MAPPINGS_FILE", "column_mappings.json")
COPQ_CONFIG_FILE = os.getenv("COPQ_CONFIG_FILE", "copq_costs.json")

# SMTP Email Dispatch settings
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "reports@smartmis.local")
SMTP_TO = os.getenv("SMTP_TO", "plant.manager@smartmis.local,quality.head@smartmis.local")
SMTP_DRY_RUN = os.getenv("SMTP_DRY_RUN", "true").lower() in ("true", "1", "yes")
