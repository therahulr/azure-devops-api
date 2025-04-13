#!/usr/bin/env python
"""
File: azure-devops-api/create_folder_structure.py
Script to create the required folder structure for the Azure DevOps CLI tool.
"""
import os
from pathlib import Path
import datetime

# Base directories
project_root = Path(__file__).parent
data_dir = project_root / 'data'
testcase_dir = data_dir / 'testcase'
archive_dir = data_dir / 'archive'
logs_dir = project_root / 'logs'
cli_dir = project_root / 'cli'

# Create directories if they don't exist
data_dir.mkdir(exist_ok=True)
testcase_dir.mkdir(exist_ok=True)
archive_dir.mkdir(exist_ok=True)
logs_dir.mkdir(exist_ok=True)
cli_dir.mkdir(exist_ok=True)

print("Created folder structure:")
print(f"- {data_dir}")
print(f"- {testcase_dir}")
print(f"- {archive_dir}")
print(f"- {logs_dir}")
print(f"- {cli_dir}")

# Ensure __init__.py files exist in needed directories
init_files = [
    project_root / 'api' / '__init__.py',
    project_root / 'cli' / '__init__.py',
    project_root / 'config' / '__init__.py',
    project_root / 'models' / '__init__.py'
]

for init_file in init_files:
    if not init_file.parent.exists():
        init_file.parent.mkdir(exist_ok=True)
        print(f"Created directory: {init_file.parent}")

    if not init_file.exists():
        with open(init_file, 'w') as f:
            f.write('"""Package initialization."""\n')
        print(f"Created: {init_file}")

# Create sample test case files for demonstration
sample_json = testcase_dir / 'sample_testcases.json'
sample_csv = testcase_dir / 'sample_testcases.csv'

# Create sample JSON file if it doesn't exist
if not sample_json.exists():
    json_content = """[
  {
    "type": "Test Case",
    "title": "Login Test",
    "description": "Verify the login functionality works as expected",
    "area_path": "YourProject\\Area",
    "iteration_path": "YourProject\\Sprint 1",
    "automation_status": "Not Automated",
    "assigned_to": "user@example.com",
    "test_steps": [
      {
        "action": "Navigate to the login page",
        "expected": "Login page is displayed with username and password fields"
      },
      {
        "action": "Enter valid username and password",
        "expected": "Credentials are accepted"
      },
      {
        "action": "Click the login button",
        "expected": "User is successfully logged in and redirected to the dashboard"
      }
    ]
  },
  {
    "type": "Test Case",
    "title": "Logout Test",
    "description": "Verify the logout functionality works as expected",
    "test_steps": [
      {
        "action": "Ensure user is logged in",
        "expected": "User is logged in and on the dashboard"
      },
      {
        "action": "Click the logout button in the user menu",
        "expected": "User is logged out and redirected to the login page"
      }
    ]
  }
]"""

    with open(sample_json, 'w') as f:
        f.write(json_content)
    print(f"Created sample JSON file: {sample_json}")

# Create sample CSV file if it doesn't exist
if not sample_csv.exists():
    csv_content = """Type,Title,Description,StepAction1,StepExpected1,StepAction2,StepExpected2,StepAction3,StepExpected3
Test Case,Login Test,Verify login functionality works as expected,Navigate to the login page,Login page is displayed with username and password fields,Enter valid username and password,Credentials are accepted,Click the login button,User is successfully logged in and redirected to the dashboard
Test Case,Logout Test,Verify logout functionality works correctly,Ensure user is logged in,User is logged in and on the dashboard,Click the logout button in the user menu,User is logged out and redirected to the login page,,"""

    with open(sample_csv, 'w') as f:
        f.write(csv_content)
    print(f"Created sample CSV file: {sample_csv}")

print("\nFolder structure setup complete. You can now place your test case files in the 'data/testcase/' directory")
print("and run the tool to create them in Azure DevOps.")