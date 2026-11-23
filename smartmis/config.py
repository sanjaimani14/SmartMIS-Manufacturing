"""SmartMIS settings."""
import os

REJECTION_TARGET = 4.0      # % - green at/below, amber up to target*1.5, red above
AMBER_LIMIT = REJECTION_TARGET * 1.5
REPORT_DIR = os.getenv("SMARTMIS_REPORT_DIR", "reports")
WEEKLY_CRON = {"day_of_week": "mon", "hour": 7}
MONTHLY_CRON = {"day": 1, "hour": 7}
COMPANY = "SmartMIS Manufacturing"

# Central database configuration
DB_PATH = os.getenv("SMARTMIS_DB_PATH", "smartmis.db")

# External PMS connection settings
PMS_DATABASE_URL = os.getenv("PMS_DATABASE_URL", "sqlite:///pms_external.db")
MOCK_PMS_URL = os.getenv("MOCK_PMS_URL", "http://127.0.0.1:8001")
COLUMN_MAPPINGS_FILE = os.getenv("COLUMN_MAPPINGS_FILE", "column_mappings.json")
