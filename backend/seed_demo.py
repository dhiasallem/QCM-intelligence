import sys
from app.services.seed_service import seed

sys.stdout.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    seed()
