"""Root forwarder for Mock PMS server."""
import sys, os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SMARTMIS_DIR = os.path.join(ROOT_DIR, "smartmis")
if SMARTMIS_DIR not in sys.path:
    sys.path.insert(0, SMARTMIS_DIR)

from mock_pms.server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
