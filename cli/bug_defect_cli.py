#!/usr/bin/env python
"""
File: azure-devops-api/cli/bug_defect_cli.py
Bug/Defect CLI - Module for managing bugs and defects in Azure DevOps.

This module provides commands for:
1. Listing available bug/defect files in data/bug_defects/ directory
2. Processing selected files to create bugs/defects in Azure DevOps
3. Moving processed files to an archive directory
"""
import os
import sys
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import API modules
from api.work_items import WorkItemClient
from config.settings import AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_ORG

# Configure logging
logs_dir = project_root / 'logs'
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f'bug_defect_cli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

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
BUG_DEFECT_DIR = DATA_DIR / 'bug_defects'
ARCHIVE_DIR = DATA_DIR / 'archive' / 'bug_defects'


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
    """Print the main menu for the Bug/Defect CLI."""
    print_title("Azure DevOps Bug/Defect Manager")
    print_info(f"Organization: {AZURE_DEVOPS_ORG}")
    print_info(f"Project: {AZURE_DEVOPS_PROJECT}")
    print("\nOptions:")
    print("  1. List available bug/defect files")
    print("  2. Process bug/defect files")
    print("  3. Create a single bug/defect")
    print("  4. Return to main menu")
    return input("\nEnter your choice (1-4): ")


def list_bug_defect_files():
    """List all bug/defect files in the data/bug_defects directory."""
    print_title("Available Bug/Defect Files")

    if not BUG_DEFECT_DIR.exists():
        print_warning(f"Directory not found: {BUG_DEFECT_DIR}")
        print_info("Creating directory...")
        BUG_DEFECT_DIR.mkdir(parents=True, exist_ok=True)
        print("Directory created. Please place your bug/defect JSON files there.")
        return []

    files = [f for f in BUG_DEFECT_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.json']

    if not files:
        print_warning("No bug/defect files found in data/bug_defects/ directory.")
        print_info("Please place JSON files containing bugs/defects in this directory.")
        return []

    print(f"Found {len(files)} bug/defect files:")
    for i, file in enumerate(files, 1):
        file_size = file.stat().st_size
        print(f"  {i}. {file.name} ({file_size / 1024:.1f} KB)")

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


def check_if_bug_defect_exists(client, title):
    """
    Check if a bug/defect with the given title already exists.

    Args:
        client: The work item client
        title: The bug/defect title

    Returns:
        tuple: (exists, id) - Boolean indicating if it exists and the ID if found
    """
    try:
        # Use a WIQL query to check if a bug/defect with this title exists
        query_str = f"""
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.TeamProject] = @project
        AND ([System.WorkItemType] = 'Bug' OR [System.WorkItemType] = 'Defect')
        AND [System.Title] = '{title.replace("'", "''")}'
        """

        # Execute the query
        wit_client = client.client
        from azure.devops.v7_1.work_item_tracking.models import Wiql
        wiql = Wiql(query=query_str)
        query_result = wit_client.query_by_wiql(wiql)

        # Check if any items were found
        if query_result.work_items and len(query_result.work_items) > 0:
            return True, query_result.work_items[0].id
        else:
            return False, None

    except Exception as e:
        logger.error(f"Error checking if bug/defect exists: {str(e)}")
        return False, None


def process_json_file(file_path, client):
    """
    Process a JSON file containing bugs/defects.

    Args:
        file_path: Path to the JSON file
        client: The work item client

    Returns:
        tuple: (created, skipped, errors)
    """
    created = []
    skipped = []
    errors = []

    try:
        # Load the JSON file
        with open(file_path, 'r') as f:
            items = json.load(f)

        # If the file contains a single object, convert to list
        if isinstance(items, dict):
            items = [items]

        print_info(f"Processing {len(items)} bugs/defects from {file_path.name}")

        # Process each bug/defect
        for i, item in enumerate(items, 1):
            item_type = item.get('type', 'Bug').strip()
            if item_type not in ['Bug', 'Defect']:
                item_type = 'Bug'  # Default to Bug if not specified or invalid

            title = item.get('title')

            if not title:
                print_warning(f"  Skipping item #{i} - No title provided")
                errors.append({
                    'index': i,
                    'title': 'No title',
                    'reason': 'Missing required field: title'
                })
                continue

            print_info(f"  Processing #{i}: {title} ({item_type})")

            # Check if the bug/defect already exists
            exists, existing_id = check_if_bug_defect_exists(client, title)

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
                # Extract bug/defect data
                description = item.get('description', '')
                steps_to_reproduce = item.get('steps_to_reproduce', '')
                system_info = item.get('system_info', '')
                assigned_to = item.get('assigned_to')
                severity = item.get('severity')
                priority = item.get('priority')
                area_path = item.get('area_path')
                iteration_path = item.get('iteration_path')
                additional_fields = item.get('additional_fields', {})

                # Create the bug/defect
                result = client.create_bug_or_defect(
                    item_type=item_type,
                    title=title,
                    description=description,
                    steps_to_reproduce=steps_to_reproduce,
                    system_info=system_info,
                    assigned_to=assigned_to,
                    severity=severity,
                    priority=priority,
                    area_path=area_path,
                    iteration_path=iteration_path,
                    additional_fields=additional_fields
                )

                print_success(f"    Created {item_type} #{result.id}")
                created.append({
                    'index': i,
                    'title': title,
                    'id': result.id,
                    'type': item_type
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
    Process selected bug/defect files.

    Args:
        files: List of file paths to process
    """
    if not files:
        return

    print_title("Processing Bug/Defect Files")

    # Initialize WorkItemClient
    client = WorkItemClient()

    total_created = 0
    total_skipped = 0
    total_errors = 0

    for file in files:
        print_title(f"Processing {file.name}")

        created, skipped, errors = process_json_file(file, client)

        # Update totals
        total_created += len(created)
        total_skipped += len(skipped)
        total_errors += len(errors)

        # Print summary for this file
        print_title(f"Summary for {file.name}")
        print_info(f"Total bugs/defects processed: {len(created) + len(skipped) + len(errors)}")
        print_success(f"Created: {len(created)}")
        print_warning(f"Skipped (already exist): {len(skipped)}")
        print_error(f"Errors: {len(errors)}")

        # Ask user if they want to archive the file
        if len(created) > 0:
            print_info("\nDo you want to archive this file now?")
            archive = input("Type 'YES' to archive, or any other key to keep: ").upper()

            if archive == 'YES':
                archive_file(file)
            else:
                print_info(f"File {file.name} kept in the bug_defects directory.")

    # Print overall summary
    print_title("Overall Summary")
    print_info(f"Total files processed: {len(files)}")
    print_success(f"Total bugs/defects created: {total_created}")
    print_warning(f"Total bugs/defects skipped: {total_skipped}")
    print_error(f"Total errors: {total_errors}")


def create_single_bug_defect():
    """Create a single bug or defect interactively."""
    print_title("Create Single Bug/Defect")

    # Initialize WorkItemClient
    client = WorkItemClient()

    # Get type
    print("\nSelect type:")
    print("  1. Bug")
    print("  2. Defect")

    type_choice = input("Enter choice (1-2): ")
    if type_choice == '1':
        item_type = 'Bug'
    elif type_choice == '2':
        item_type = 'Defect'
    else:
        print_error("Invalid choice. Defaulting to Bug.")
        item_type = 'Bug'

    # Get required fields
    title = input("\nEnter title: ")
    if not title:
        print_error("Title is required.")
        return

    # Get optional fields
    description = input("Enter description (press Enter to skip): ")
    steps_to_reproduce = input("Enter steps to reproduce (press Enter to skip): ")
    system_info = input("Enter system info (press Enter to skip): ")
    assigned_to = input("Enter assigned to (email or name, press Enter to skip): ")

    severity_options = {
        '1': '1 - Critical',
        '2': '2 - High',
        '3': '3 - Medium',
        '4': '4 - Low'
    }
    print("\nSeverity options:")
    for key, value in severity_options.items():
        print(f"  {key}. {value}")

    severity_choice = input("Select severity (1-4, press Enter to skip): ")
    severity = severity_options.get(severity_choice)

    priority = input("Enter priority (1-4, press Enter to skip): ")
    if priority:
        try:
            priority = int(priority)
        except ValueError:
            print_warning("Priority must be a number. Setting to default.")
            priority = None
    else:
        priority = None

    area_path = input("Enter area path (press Enter to use default): ")
    iteration_path = input("Enter iteration path (press Enter to use default): ")

    try:
        # Check if bug/defect already exists
        exists, existing_id = check_if_bug_defect_exists(client, title)

        if exists:
            print_warning(f"Bug/defect with title '{title}' already exists with ID {existing_id}.")
            return

        # Create the bug/defect
        result = client.create_bug_or_defect(
            item_type=item_type,
            title=title,
            description=description,
            steps_to_reproduce=steps_to_reproduce,
            system_info=system_info,
            assigned_to=assigned_to,
            severity=severity,
            priority=priority,
            area_path=area_path if area_path else None,
            iteration_path=iteration_path if iteration_path else None
        )

        print_success(f"Created {item_type} #{result.id}: {title}")

        # Ask if the user wants to export the newly created bug/defect
        export_option = input("\nDo you want to export the details of this bug/defect? (y/n): ").lower()
        if export_option == 'y':
            export_path = client.export_work_item_details(result.id)
            print_success(f"Bug/defect exported to: {export_path}")

    except Exception as e:
        print_error(f"Error creating bug/defect: {str(e)}")


def main():
    """Main entry point for the Bug/Defect CLI."""
    # Ensure data directories exist
    DATA_DIR.mkdir(exist_ok=True)
    BUG_DEFECT_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        choice = print_menu()

        if choice == '1':
            list_bug_defect_files()
            input("\nPress Enter to continue...")

        elif choice == '2':
            files = list_bug_defect_files()
            selected_files = select_files(files)
            if selected_files:
                process_files(selected_files)
            input("\nPress Enter to continue...")

        elif choice == '3':
            create_single_bug_defect()
            input("\nPress Enter to continue...")

        elif choice == '4':
            print_info("Returning to main menu.")
            break

        else:
            print_warning("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()