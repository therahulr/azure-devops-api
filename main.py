#!/usr/bin/env python
"""
File: azure-devops-api/main.py
Azure DevOps CLI - Main router for module-specific CLI tools.

This script acts as a router to launch module-specific CLI tools
for different aspects of Azure DevOps integration.
"""
import os
import sys
import logging
import importlib
from pathlib import Path
from datetime import datetime

# Configure logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'azure_devops_cli_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import settings
sys.path.append(str(Path(__file__).parent))
from config.settings import AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_ORG

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
    """Print the main menu for the Azure DevOps CLI."""
    print_title("Azure DevOps CLI")
    print_info(f"Organization: {AZURE_DEVOPS_ORG}")
    print_info(f"Project: {AZURE_DEVOPS_PROJECT}")
    print("\nSelect a module to work with:")
    print("  1. Test Case Management")
    print("  2. Work Item Management")
    print("  3. Bug/Defect Management")
    print("  4. Exit")
    return input("\nEnter your choice (1-4): ")


def launch_test_case_cli():
    """Launch the Test Case CLI module."""
    try:
        from cli.test_case_cli import main as test_case_main
        test_case_main()
    except ImportError:
        print_error("Test Case CLI module not found.")
        logger.error("Failed to import cli.test_case_cli module.", exc_info=True)
    except Exception as e:
        print_error(f"Error in Test Case CLI: {str(e)}")
        logger.error(f"Error in Test Case CLI: {str(e)}", exc_info=True)


def launch_work_item_cli():
    """Launch the Work Item CLI module."""
    try:
        from cli.work_item_cli import main as work_item_main
        work_item_main()
    except ImportError:
        print_error("Work Item CLI module not found.")
        logger.error("Failed to import cli.work_item_cli module.", exc_info=True)
    except Exception as e:
        print_error(f"Error in Work Item CLI: {str(e)}")
        logger.error(f"Error in Work Item CLI: {str(e)}", exc_info=True)


def launch_bug_defect_cli():
    """Launch the Bug/Defect CLI module."""
    try:
        from cli.bug_defect_cli import main as bug_defect_main
        bug_defect_main()
    except ImportError:
        print_error("Bug/Defect CLI module not found.")
        logger.error("Failed to import cli.bug_defect_cli module.", exc_info=True)
    except Exception as e:
        print_error(f"Error in Bug/Defect CLI: {str(e)}")
        logger.error(f"Error in Bug/Defect CLI: {str(e)}", exc_info=True)


def main():
    """Main entry point for the Azure DevOps CLI router."""
    # Ensure necessary directories exist
    work_item_dir = Path(__file__).parent / 'WorkItem'
    work_item_dir.mkdir(exist_ok=True)

    # Create data directories for bug/defect management
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)

    bug_defect_dir = data_dir / 'bug_defects'
    bug_defect_dir.mkdir(exist_ok=True)

    archive_dir = data_dir / 'archive'
    archive_dir.mkdir(exist_ok=True)

    bug_defect_archive_dir = archive_dir / 'bug_defects'
    bug_defect_archive_dir.mkdir(exist_ok=True)

    while True:
        choice = print_menu()

        if choice == '1':
            launch_test_case_cli()

        elif choice == '2':
            launch_work_item_cli()

        elif choice == '3':
            launch_bug_defect_cli()

        elif choice == '4':
            print_info("Exiting Azure DevOps CLI.")
            break

        else:
            print_warning("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()