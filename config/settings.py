"""
Configuration settings for Azure DevOps API integration.
"""
import os
import json
from pathlib import Path

# Base directories
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / 'config'
TEMPLATES_DIR = ROOT_DIR / 'templates'
print(f"Root directory: {ROOT_DIR}")
print(f"Config directory: {CONFIG_DIR}")
print(f"Templates directory: {TEMPLATES_DIR}")

# Load credentials from JSON file (if exists)
CREDENTIALS_FILE = CONFIG_DIR / 'credentials.json'
print(f"Loading credentials from {CREDENTIALS_FILE}")
CREDENTIALS = {}

if CREDENTIALS_FILE.exists():
    with open(CREDENTIALS_FILE, 'r') as f:
        CREDENTIALS = json.load(f)

# Azure DevOps settings
# Try to get from credentials file first, then environment variables
AZURE_DEVOPS_ORG = CREDENTIALS.get('organization_url', os.environ.get('AZURE_DEVOPS_ORG', ''))
AZURE_DEVOPS_PAT = CREDENTIALS.get('personal_access_token', os.environ.get('AZURE_DEVOPS_PAT', ''))
AZURE_DEVOPS_PROJECT = CREDENTIALS.get('project', os.environ.get('AZURE_DEVOPS_PROJECT', ''))
AZURE_DEVOPS_API_VERSION = CREDENTIALS.get('api_version', os.environ.get('AZURE_DEVOPS_API_VERSION', '7.1'))

# Validate required settings
if not AZURE_DEVOPS_ORG or not AZURE_DEVOPS_PAT or not AZURE_DEVOPS_PROJECT:
    print("WARNING: Azure DevOps settings not fully configured.")
    print("Please set the following:")
    if not AZURE_DEVOPS_ORG:
        print("- Organization URL (AZURE_DEVOPS_ORG)")
    if not AZURE_DEVOPS_PAT:
        print("- Personal Access Token (AZURE_DEVOPS_PAT)")
    if not AZURE_DEVOPS_PROJECT:
        print("- Project Name (AZURE_DEVOPS_PROJECT)")