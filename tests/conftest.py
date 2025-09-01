import os
from dotenv import load_dotenv

def pytest_configure(config):
    # Load .env file before any tests are collected or run
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)
