#!/usr/bin/env python
"""
File: azure-devops-api/cli/work_item_cli.py
Work Item CLI - Module for managing and exporting work items from Azure DevOps.

This module provides commands for:
1. Exporting work item details and attachments to the WorkItem folder
2. Creating new work items (User Stories, Bugs, Tasks)
3. Updating existing work items
"""
import os
import sys
import logging
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
log_file = logs_dir / f'work_item_cli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

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
    """Print the main menu for the Work Item CLI."""
    print_title("Azure DevOps Work Item Manager")
    print_info(f"Organization: {AZURE_DEVOPS_ORG}")
    print_info(f"Project: {AZURE_DEVOPS_PROJECT}")
    print("\nOptions:")
    print("  1. Export work item details and attachments")
    print("  2. Create new work item")
    print("  3. Update existing work item")
    print("  4. Bulk export multiple work items")
    print("  5. Return to main menu")
    return input("\nEnter your choice (1-5): ")


def export_work_item():
    """Export work item details and attachments."""
    print_title("Export Work Item")

    # Initialize WorkItemClient
    client = WorkItemClient()

    try:
        # Get work item ID
        work_item_id = int(input("Enter work item ID to export: "))

        print_info(f"Exporting work item #{work_item_id}...")

        # Call the export function
        export_path = client.export_work_item_details(work_item_id)

        print_success(f"Work item #{work_item_id} exported successfully!")
        print_info(f"Export location: {export_path}")

        # Ask if user wants to open the folder
        open_folder = input("\nDo you want to open the export folder? (y/n): ").lower()
        if open_folder == 'y':
            # Open the folder in file explorer (platform-specific)
            if sys.platform == 'win32':
                os.startfile(export_path)
            elif sys.platform == 'darwin':  # macOS
                import subprocess
                subprocess.call(['open', export_path])
            else:  # Linux
                import subprocess
                subprocess.call(['xdg-open', export_path])

    except ValueError:
        print_error("Invalid work item ID. Please enter a number.")
    except Exception as e:
        print_error(f"Error exporting work item: {str(e)}")


def create_work_item():
    """Create a new work item."""
    print_title("Create New Work Item")

    # Initialize WorkItemClient
    client = WorkItemClient()

    # Select work item type
    print("\nSelect work item type:")
    print("  1. User Story")
    print("  2. Bug")
    print("  3. Task")
    print("  4. Custom")

    type_choice = input("\nEnter your choice (1-4): ")

    work_item_type = ""
    if type_choice == '1':
        work_item_type = "User Story"
    elif type_choice == '2':
        work_item_type = "Bug"
    elif type_choice == '3':
        work_item_type = "Task"
    elif type_choice == '4':
        work_item_type = input("Enter custom work item type: ")
    else:
        print_error("Invalid choice.")
        return

    # Get common fields
    title = input("\nEnter title: ")
    if not title:
        print_error("Title is required.")
        return

    description = input("Enter description (press Enter to skip): ")
    assigned_to = input("Enter assigned to (email or name, press Enter to skip): ")
    area_path = input("Enter area path (press Enter to use default): ")
    iteration_path = input("Enter iteration path (press Enter to use default): ")

    # Type-specific fields
    additional_fields = {}

    if work_item_type == "User Story":
        acceptance_criteria = input("Enter acceptance criteria (press Enter to skip): ")
        if acceptance_criteria:
            additional_fields["Microsoft.VSTS.Common.AcceptanceCriteria"] = acceptance_criteria

        business_value = input("Enter business value (1-10, press Enter to skip): ")
        if business_value:
            try:
                additional_fields["Microsoft.VSTS.Common.BusinessValue"] = int(business_value)
            except ValueError:
                print_warning("Business value must be a number. Skipping.")

    elif work_item_type == "Bug":
        steps = input("Enter reproduction steps (press Enter to skip): ")
        if steps:
            additional_fields["Microsoft.VSTS.TCM.ReproSteps"] = steps

        severity = input("Enter severity (1 - Critical, 2 - High, 3 - Medium, 4 - Low, press Enter to skip): ")
        if severity:
            additional_fields["Microsoft.VSTS.Common.Severity"] = severity

        priority = input("Enter priority (1, 2, 3, 4, press Enter to skip): ")
        if priority:
            try:
                additional_fields["Microsoft.VSTS.Common.Priority"] = int(priority)
            except ValueError:
                print_warning("Priority must be a number. Skipping.")

    # Create the work item
    try:
        work_item = client.create_work_item(
            work_item_type=work_item_type,
            title=title,
            description=description,
            assigned_to=assigned_to if assigned_to else None,
            area_path=area_path if area_path else None,
            iteration_path=iteration_path if iteration_path else None,
            additional_fields=additional_fields if additional_fields else None
        )

        print_success(f"Created {work_item_type} #{work_item.id}: {title}")

        # Ask if the user wants to export the newly created work item
        export_option = input("\nDo you want to export the details of this work item? (y/n): ").lower()
        if export_option == 'y':
            export_path = client.export_work_item_details(work_item.id)
            print_success(f"Work item exported to: {export_path}")

    except Exception as e:
        print_error(f"Error creating work item: {str(e)}")


def update_work_item():
    """Update an existing work item."""
    print_title("Update Work Item")

    # Initialize WorkItemClient
    client = WorkItemClient()

    try:
        # Get work item ID
        work_item_id = int(input("Enter work item ID to update: "))

        # Get the current work item to show its details
        try:
            work_item = client.get_work_item(work_item_id)
            fields = work_item.fields

            print_info(f"\nCurrent details for work item #{work_item_id}:")
            print(f"Title: {fields.get('System.Title', 'N/A')}")
            print(f"State: {fields.get('System.State', 'N/A')}")
            print(f"Work Item Type: {fields.get('System.WorkItemType', 'N/A')}")

            assigned_to = fields.get('System.AssignedTo', {})
            if isinstance(assigned_to, dict):
                assigned_to = assigned_to.get('displayName', 'Unassigned')
            print(f"Assigned To: {assigned_to}")

        except Exception as e:
            print_error(f"Failed to retrieve work item #{work_item_id}: {str(e)}")
            return

        # Ask which fields to update
        print("\nSelect fields to update (leave blank to skip):")

        # Common fields
        new_title = input("New Title: ")
        new_description = input("New Description: ")
        new_state = input("New State: ")
        new_assigned_to = input("New Assigned To: ")

        # Build updates dictionary
        updates = {}

        if new_title:
            updates['System.Title'] = new_title

        if new_description:
            updates['System.Description'] = new_description

        if new_state:
            updates['System.State'] = new_state

        if new_assigned_to:
            updates['System.AssignedTo'] = new_assigned_to

        # Check if there are any updates
        if not updates:
            print_warning("No updates provided.")
            return

        # Confirm updates
        print_info("\nThe following updates will be applied:")
        for field, value in updates.items():
            print(f"  {field}: {value}")

        confirm = input("\nConfirm updates? (y/n): ").lower()
        if confirm != 'y':
            print_info("Update cancelled.")
            return

        # Update the work item
        updated_work_item = client.update_work_item(work_item_id, updates)
        print_success(f"Work item #{work_item_id} updated successfully!")

        # Ask if the user wants to export the updated work item
        export_option = input("\nDo you want to export the updated work item? (y/n): ").lower()
        if export_option == 'y':
            export_path = client.export_work_item_details(work_item_id)
            print_success(f"Updated work item exported to: {export_path}")

    except ValueError:
        print_error("Invalid work item ID. Please enter a number.")
    except Exception as e:
        print_error(f"Error updating work item: {str(e)}")


def bulk_export_work_items():
    """Export multiple work items in a batch."""
    print_title("Bulk Export Work Items")

    # Initialize WorkItemClient
    client = WorkItemClient()

    try:
        # Get work item IDs
        ids_input = input("Enter work item IDs (comma-separated): ")
        id_list = [int(id.strip()) for id in ids_input.split(',') if id.strip()]

        if not id_list:
            print_warning("No valid work item IDs provided.")
            return

        print_info(f"Preparing to export {len(id_list)} work items...")

        export_paths = []
        for work_item_id in id_list:
            try:
                print_info(f"Exporting work item #{work_item_id}...")
                export_path = client.export_work_item_details(work_item_id)
                export_paths.append(export_path)
                print_success(f"Work item #{work_item_id} exported successfully!")
            except Exception as e:
                print_error(f"Failed to export work item #{work_item_id}: {str(e)}")

        if export_paths:
            print_success(f"Successfully exported {len(export_paths)} out of {len(id_list)} work items.")
        else:
            print_error("Failed to export any work items.")

    except ValueError:
        print_error("Invalid work item ID format. Please enter comma-separated numbers.")
    except Exception as e:
        print_error(f"Error in bulk export: {str(e)}")


def main():
    """Main entry point for the Work Item CLI."""
    # Ensure WorkItem directory exists at project root
    work_item_dir = Path(project_root) / 'WorkItem'
    work_item_dir.mkdir(exist_ok=True)

    while True:
        choice = print_menu()

        if choice == '1':
            export_work_item()
            input("\nPress Enter to continue...")

        elif choice == '2':
            create_work_item()
            input("\nPress Enter to continue...")

        elif choice == '3':
            update_work_item()
            input("\nPress Enter to continue...")

        elif choice == '4':
            bulk_export_work_items()
            input("\nPress Enter to continue...")

        elif choice == '5':
            print_info("Returning to main menu.")
            break

        else:
            print_warning("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()