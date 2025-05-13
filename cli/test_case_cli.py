#!/usr/bin/env python
"""
File: azure-devops-api/cli/test_case_cli.py
Test Case CLI - Module for managing test cases in Azure DevOps.

This module provides commands for:
1. Listing available test case files in data/testcase/ directory
2. Processing selected files to create test cases in Azure DevOps
3. Moving processed files to an archive directory
"""
import os
import sys
import json
import csv
import logging
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import API modules
from api.test_cases import TestCaseClient
from api.auth import get_connection
from config.settings import AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_ORG

# Configure logging
logs_dir = project_root / 'logs'
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f'test_case_cli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ANSI escape sequences for colored output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
END = '\033[0m'

# Directory paths
DATA_DIR = project_root / 'data'
TESTCASE_DIR = DATA_DIR / 'testcase'
ARCHIVE_DIR = DATA_DIR / 'archive'


def print_success(message):
    """Print a success message in green."""
    print(f"{GREEN}{message}{END}")


def print_warning(message):
    """Print a warning message in yellow."""
    print(f"{YELLOW}{message}{END}")


def print_error(message):
    """Print an error message in red."""
    print(f"{RED}{message}{END}")


def print_info(message):
    """Print an info message in blue."""
    print(f"{BLUE}{message}{END}")


def print_title(title):
    """Print a section title."""
    print(f"\n{BOLD}{UNDERLINE}{title}{END}")


def print_menu():
    """Print the main menu for the Test Case CLI."""
    print_title("Azure DevOps Test Case Manager")
    print_info(f"Organization: {AZURE_DEVOPS_ORG}")
    print_info(f"Project: {AZURE_DEVOPS_PROJECT}")
    print("\nOptions:")
    print("  1. List available test case files")
    print("  2. Process test case files")
    print("  3. Link test cases to parent work item")
    print("  4. Return to main menu")
    return input("\nEnter your choice (1-4): ")

def list_testcase_files():
    """List all test case files in the data/testcase directory."""
    print_title("Available Test Case Files")

    if not TESTCASE_DIR.exists():
        print_warning(f"Directory not found: {TESTCASE_DIR}")
        print_info("Creating directory...")
        TESTCASE_DIR.mkdir(parents=True, exist_ok=True)
        print("Directory created. Please place your test case files there.")
        return []

    files = [f for f in TESTCASE_DIR.iterdir() if f.is_file() and f.suffix.lower() in ['.json', '.csv']]

    if not files:
        print_warning("No test case files found in data/testcase/ directory.")
        print_info("Please place JSON or CSV files containing test cases in this directory.")
        return []

    print(f"Found {len(files)} test case files:")
    for i, file in enumerate(files, 1):
        file_size = file.stat().st_size
        file_type = file.suffix.upper()[1:]  # Remove the dot from suffix
        print(f"  {i}. {file.name} ({file_type}, {file_size / 1024:.1f} KB)")

    return files


def select_files(files):
    """Allow user to select which files to process."""
    if not files:
        return []

    print_title("Select Files to Process")
    print("Options:")
    print("  A. Process all files")
    print("  S. Select specific files (comma-separated numbers)")
    print("  X. Return to main menu")

    choice = input("\nEnter your choice: ").upper()

    if choice == 'A':
        print_warning(f"You've selected to process ALL {len(files)} files. Are you sure?")
        confirm = input("Type 'YES' to confirm: ").upper()
        if confirm == 'YES':
            return files
        else:
            print_info("Operation cancelled.")
            return []
    elif choice == 'S':
        try:
            indices = input("Enter file numbers to process (comma-separated): ")
            selected_indices = [int(idx.strip()) for idx in indices.split(',')]
            selected_files = [files[idx - 1] for idx in selected_indices if 1 <= idx <= len(files)]

            if not selected_files:
                print_warning("No valid files selected.")
                return []

            print_info(f"Selected {len(selected_files)} files:")
            for i, file in enumerate(selected_files, 1):
                print(f"  {i}. {file.name}")

            return selected_files
        except (ValueError, IndexError) as e:
            print_error(f"Invalid selection: {str(e)}")
            return []
    else:
        return []


def link_test_cases():
    """Link test cases to a parent work item."""
    print_title("Link Test Cases to Parent Work Item")

    # Initialize TestCaseClient
    client = TestCaseClient()

    # Get parent work item ID
    try:
        parent_id = int(input("Enter parent work item ID (e.g., User Story): "))
    except ValueError:
        print_error("Invalid ID. Please enter a number.")
        return

    # Get test case IDs
    try:
        test_case_ids_input = input("Enter test case IDs (comma-separated): ")
        test_case_ids = [int(id.strip()) for id in test_case_ids_input.split(',') if id.strip()]

        if not test_case_ids:
            print_warning("No valid test case IDs provided.")
            return

        print_info(f"Linking {len(test_case_ids)} test cases to parent work item #{parent_id}...")

        # Confirm
        confirm = input("Type 'YES' to confirm: ").upper()
        if confirm != 'YES':
            print_info("Operation cancelled.")
            return

        # Link test cases
        updated_work_item = client.link_test_cases_to_parent(parent_id, test_case_ids)

        print_success(f"Successfully linked test cases to parent work item #{parent_id}")

    except Exception as e:
        print_error(f"Error linking test cases: {str(e)}")


def check_if_testcase_exists(client, title):
    """
    Check if a test case with the given title already exists.

    Args:
        client: The test case client
        title: The test case title

    Returns:
        tuple: (exists, id) - Boolean indicating if it exists and the ID if found
    """
    try:
        # Use a WIQL query to check if a test case with this title exists
        query_str = f"""
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.TeamProject] = @project
        AND [System.WorkItemType] = 'Test Case'
        AND [System.Title] = '{title.replace("'", "''")}'
        """

        # Execute the query
        wit_client = client.wit_client
        from azure.devops.v7_1.work_item_tracking.models import Wiql
        wiql = Wiql(query=query_str)
        query_result = wit_client.query_by_wiql(wiql)

        # Check if any items were found
        if query_result.work_items and len(query_result.work_items) > 0:
            return True, query_result.work_items[0].id
        else:
            return False, None

    except Exception as e:
        logger.error(f"Error checking if test case exists: {str(e)}")
        return False, None


def process_json_file(file_path, client):
    """
    Process a JSON file containing test cases.

    Args:
        file_path: Path to the JSON file
        client: The test case client

    Returns:
        tuple: (created, skipped, errors)
    """
    created = []
    skipped = []
    errors = []

    try:
        # Load the JSON file
        with open(file_path, 'r') as f:
            test_cases = json.load(f)

        print_info(f"Processing {len(test_cases)} test cases from {file_path.name}")

        # Process each test case
        for i, tc in enumerate(test_cases, 1):
            title = tc.get('title')

            if not title:
                print_warning(f"  Skipping test case #{i} - No title provided")
                errors.append({
                    'index': i,
                    'title': 'No title',
                    'reason': 'Missing required field: title'
                })
                continue

            print_info(f"  Processing #{i}: {title}")

            # Check if the test case already exists
            exists, existing_id = check_if_testcase_exists(client, title)

            if exists:
                print_warning(f"    Skipping - Already exists with ID {existing_id}")
                skipped.append({
                    'index': i,
                    'title': title,
                    'id': existing_id,
                    'reason': 'Already exists'
                })
                continue

            try:
                # Extract test case data
                description = tc.get('description', '')
                area_path = tc.get('area_path')
                iteration_path = tc.get('iteration_path')
                automation_status = tc.get('automation_status')
                test_steps = tc.get('test_steps', [])
                additional_fields = tc.get('additional_fields', {})

                # Create the test case
                test_case = client.create_test_case(
                    title=title,
                    description=description,
                    area_path=area_path,
                    iteration_path=iteration_path,
                    test_steps=test_steps,
                    automation_status=automation_status,
                    additional_fields=additional_fields
                )

                print_success(f"    Created Test Case #{test_case.id}")
                created.append({
                    'index': i,
                    'title': title,
                    'id': test_case.id,
                    'steps': len(test_steps)
                })

            except Exception as e:
                print_error(f"    Error: {str(e)}")
                errors.append({
                    'index': i,
                    'title': title,
                    'reason': str(e)
                })

        return created, skipped, errors

    except Exception as e:
        print_error(f"Error processing JSON file: {str(e)}")
        return created, skipped, errors


def process_csv_file(file_path, client):
    """
    Process a CSV file containing test cases.

    Args:
        file_path: Path to the CSV file
        client: The test case client

    Returns:
        tuple: (created, skipped, errors)
    """
    created = []
    skipped = []
    errors = []

    try:
        # Load the CSV file
        df = pd.read_csv(file_path)

        # Check for required columns
        if 'Title' not in df.columns:
            print_error("CSV file must contain a 'Title' column")
            return created, skipped, errors

        print_info(f"Processing {len(df)} test cases from {file_path.name}")

        # Process each row
        for i, row in df.iterrows():
            title = row.get('Title')

            if pd.isna(title) or not title:
                print_warning(f"  Skipping row {i + 2} - No title provided")
                errors.append({
                    'index': i + 2,
                    'title': 'No title',
                    'reason': 'Missing required field: title'
                })
                continue

            print_info(f"  Processing row {i + 2}: {title}")

            # Check if the test case already exists
            exists, existing_id = check_if_testcase_exists(client, title)

            if exists:
                print_warning(f"    Skipping - Already exists with ID {existing_id}")
                skipped.append({
                    'index': i + 2,
                    'title': title,
                    'id': existing_id,
                    'reason': 'Already exists'
                })
                continue

            try:
                # Extract test case data
                description = row.get('Description', '')
                if pd.isna(description):
                    description = ''

                area_path = row.get('AreaPath')
                if pd.isna(area_path):
                    area_path = None

                iteration_path = row.get('IterationPath')
                if pd.isna(iteration_path):
                    iteration_path = None

                automation_status = row.get('AutomationStatus')
                if pd.isna(automation_status):
                    automation_status = None

                # Extract test steps
                test_steps = []
                step_columns = [col for col in df.columns if col.startswith('StepAction')]

                for j, action_col in enumerate(sorted(step_columns), 1):
                    # Find the matching expected column
                    expected_col = f'StepExpected{action_col[10:]}' if len(action_col) > 10 else 'StepExpected'

                    if expected_col in df.columns:
                        action = row.get(action_col)
                        expected = row.get(expected_col)

                        if not pd.isna(action) and action:
                            test_steps.append({
                                'action': action,
                                'expected': '' if pd.isna(expected) else expected
                            })

                # Create the test case
                test_case = client.create_test_case(
                    title=title,
                    description=description,
                    area_path=area_path,
                    iteration_path=iteration_path,
                    test_steps=test_steps,
                    automation_status=automation_status
                )

                print_success(f"    Created Test Case #{test_case.id}")
                created.append({
                    'index': i + 2,
                    'title': title,
                    'id': test_case.id,
                    'steps': len(test_steps)
                })

            except Exception as e:
                print_error(f"    Error: {str(e)}")
                errors.append({
                    'index': i + 2,
                    'title': title,
                    'reason': str(e)
                })

        return created, skipped, errors

    except Exception as e:
        print_error(f"Error processing CSV file: {str(e)}")
        return created, skipped, errors


def archive_file(file_path):
    """
    Move a processed file to the archive directory.

    Args:
        file_path: Path to the file to archive

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create archive directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = ARCHIVE_DIR / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Move the file
        destination = archive_dir / file_path.name
        shutil.move(str(file_path), str(destination))

        print_info(f"Archived {file_path.name} to {archive_dir}")
        return True

    except Exception as e:
        print_error(f"Error archiving file {file_path.name}: {str(e)}")
        return False


def process_files(files):
    """
    Process selected test case files.

    Args:
        files: List of file paths to process
    """
    if not files:
        return

    print_title("Processing Test Case Files")

    # Initialize TestCaseClient
    client = TestCaseClient()

    total_created = 0
    total_skipped = 0
    total_errors = 0
    
    # Track successfully processed files
    successfully_processed = []

    for file in files:
        print_title(f"Processing {file.name}")

        created = []
        skipped = []
        errors = []

        # Process based on file type
        if file.suffix.lower() == '.json':
            created, skipped, errors = process_json_file(file, client)
        elif file.suffix.lower() == '.csv':
            created, skipped, errors = process_csv_file(file, client)
        else:
            print_error(f"Unsupported file type: {file.suffix}")
            continue

        # Update totals
        total_created += len(created)
        total_skipped += len(skipped)
        total_errors += len(errors)

        # Print summary for this file
        print_title(f"Summary for {file.name}")
        print_info(f"Total test cases processed: {len(created) + len(skipped) + len(errors)}")
        print_success(f"Created: {len(created)}")
        print_warning(f"Skipped (already exist): {len(skipped)}")
        print_error(f"Errors: {len(errors)}")
        
        # Add to successfully processed list if any test cases were created
        if len(created) > 0:
            successfully_processed.append(file)

    # Print overall summary
    print_title("Overall Summary")
    print_info(f"Total files processed: {len(files)}")
    print_success(f"Total test cases created: {total_created}")
    print_warning(f"Total test cases skipped: {total_skipped}")
    print_error(f"Total errors: {total_errors}")
    
    # Ask about archiving all successfully processed files AFTER the loop
    if successfully_processed:
        print_info(f"\nDo you want to archive all {len(successfully_processed)} successfully processed files now?")
        archive = input("Type 'YES' to archive, or any other key to keep: ").upper()

        if archive == 'YES':
            for file in successfully_processed:
                archive_file(file)
            print_success(f"Archived {len(successfully_processed)} files.")
        else:
            print_info("Files kept in the testcase directory.")


def main():
    """Main entry point for the Test Case CLI."""
    # Ensure data directories exist
    DATA_DIR.mkdir(exist_ok=True)
    TESTCASE_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

    while True:
        choice = print_menu()

        if choice == '1':
            list_testcase_files()
            input("\nPress Enter to continue...")

        elif choice == '2':
            files = list_testcase_files()
            selected_files = select_files(files)
            if selected_files:
                process_files(selected_files)
            input("\nPress Enter to continue...")

        elif choice == '3':
            link_test_cases()
            input("\nPress Enter to continue...")

        elif choice == '4':
            print_info("Returning to main menu.")
            break

        else:
            print_warning("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()