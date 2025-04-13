# Azure DevOps CLI Guide

## Overview

The Azure DevOps CLI is a command-line tool for managing work items, test cases, and other artifacts in Azure DevOps. It provides a simple interface to perform common operations like creating and updating work items, managing test cases, and working with test plans and suites.

## Prerequisites

- Python 3.7+
- Personal Access Token (PAT) for Azure DevOps
- Azure DevOps organization and project

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your Azure DevOps credentials in `config/credentials.json`:
   ```json
   {
       "organization_url": "https://dev.azure.com/YOUR_ORGANIZATION",
       "personal_access_token": "YOUR_PAT_HERE",
       "project": "YOUR_PROJECT_NAME",
       "api_version": "7.1"
   }
   ```

## Key Features

- **Work Item Management**: Create, update, and link work items
- **Test Case Management**: Create test cases, manage test steps
- **Test Plan/Suite Integration**: Work with test plans and suites
- **Bulk Operations**: Create multiple work items or test cases at once

## Command Reference

### Work Item Management

| Command | Description | Example |
|---------|-------------|---------|
| `create-work-item` | Create a new work item | `python main.py create-work-item --type "User Story" --title "Implement login feature"` |
| `update-work-item` | Update an existing work item | `python main.py update-work-item --id 123 --updates-file updates.json` |
| `create-child` | Create a child work item | `python main.py create-child --parent-id 123 --type "Task" --title "Design login UI"` |
| `create-bug` | Create a new bug | `python main.py create-bug --title "Login fails on mobile" --severity "2 - High"` |
| `get-story` | Get user story details | `python main.py get-story --id 123` |

### Test Case Management

| Command | Description | Example |
|---------|-------------|---------|
| `create-test-case` | Create a new test case | `python main.py create-test-case --title "Verify login functionality" --steps-file steps.json` |
| `update-test-steps` | Update test steps | `python main.py update-test-steps --id 123 --steps-file steps.json` |
| `bulk-test-cases` | Create multiple test cases | `python main.py bulk-test-cases --file test_cases.json` |

### Test Plans and Suites

| Command | Description | Example |
|---------|-------------|---------|
| `list-plans` | List all test plans | `python main.py list-plans` |
| `list-suites` | List test suites in a plan | `python main.py list-suites --plan-id 123` |
| `list-cases` | List test cases in a suite | `python main.py list-cases --plan-id 123 --suite-id 456` |
| `add-to-suite` | Add a test case to a suite | `python main.py add-to-suite --id 789 --plan-id 123 --suite-id 456` |

### Utilities

| Command | Description | Example |
|---------|-------------|---------|
| `generate-constants` | Generate constants from the current project | `python main.py generate-constants` |

## File Templates

### Work Item Fields (JSON)
```json
{
    "Microsoft.VSTS.Common.Priority": 2,
    "System.Tags": "Feature; UI"
}
```

### Test Steps (JSON)
```json
[
    {
        "action": "Navigate to the login page",
        "expected": "Login page is displayed"
    },
    {
        "action": "Enter valid username and password",
        "expected": "Credentials are accepted"
    },
    {
        "action": "Click the login button",
        "expected": "User is logged in and redirected to dashboard"
    }
]
```

### Bulk Test Cases (JSON)
```json
[
    {
        "title": "Login Test",
        "description": "Test the login functionality",
        "test_steps": [
            {"action": "Action 1", "expected": "Expected 1"},
            {"action": "Action 2", "expected": "Expected 2"}
        ]
    },
    {
        "title": "Logout Test",
        "description": "Test the logout functionality",
        "test_steps": [
            {"action": "Login to the application", "expected": "User is logged in"},
            {"action": "Click logout button", "expected": "User is logged out"}
        ]
    }
]
```

## Common Workflows

### 1. Creating a User Story with Child Tasks

```bash
# Create a user story
python main.py create-work-item --type "User Story" --title "Implement login functionality" --description "As a user, I want to log in to the system"

# Create child tasks (replace 123 with the actual user story ID)
python main.py create-child --parent-id 123 --type "Task" --title "Design login UI"
python main.py create-child --parent-id 123 --type "Task" --title "Implement authentication logic"
python main.py create-child --parent-id 123 --type "Task" --title "Add validation for login form"
```

### 2. Creating Test Cases for a Feature

```bash
# Create a test case with steps
python main.py create-test-case --title "Verify login functionality" --steps-file templates/login_test_steps.json

# Add the test case to a test suite
python main.py add-to-suite --id 456 --plan-id 123 --suite-id 789
```

### 3. Reporting a Bug

```bash
python main.py create-bug --title "Login fails on mobile devices" --severity "2 - High" --priority 1 --steps-to-reproduce "1. Open app on mobile\n2. Enter credentials\n3. Click login"
```
