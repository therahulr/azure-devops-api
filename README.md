# Azure DevOps API Integration

A modular command-line tool for interacting with Azure DevOps APIs to manage work items, test cases, and more.

## Features

- **Test Case Management**: Create and update test cases with steps
- **Bulk Import**: Import test cases from JSON or CSV files
- **Duplicate Detection**: Skip test cases that already exist
- **Interactive UI**: Menu-driven interface for easy navigation
- **File Archiving**: Automatically archive processed files

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/azure-devops-api.git
   cd azure-devops-api
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure your Azure DevOps credentials:
   ```bash
   # Create config/credentials.json with your organization URL, PAT, and project
   {
       "organization_url": "https://dev.azure.com/YOUR_ORGANIZATION",
       "personal_access_token": "YOUR_PAT_HERE",
       "project": "YOUR_PROJECT_NAME",
       "api_version": "7.1"
   }
   ```

4. Set up the folder structure:
   ```bash
   python create_folder_structure.py
   ```

## Usage

Run the main CLI tool:
```bash
python main.py
```

### Test Case Management

1. Select "Test Case Management" from the main menu
2. Choose to list available files or process files
3. Select files to process
4. Review results and choose whether to archive processed files

## Project Structure

```
azure-devops-api/
│
├── api/                      # API modules
│   ├── auth.py               # Authentication
│   ├── azure_devops_core_queries.py  # Core query functions
│   ├── test_cases.py         # Test case operations
│   └── work_items.py         # Work item operations
│
├── cli/                      # CLI modules
│   └── test_case_cli.py      # Test case management CLI
│
├── config/                   # Configuration
│   ├── credentials.json      # Your credentials (gitignored)
│   └── settings.py           # Settings parser
│
├── data/                     # Data files
│   ├── archive/              # Archived processed files
│   └── testcase/             # Input test case files
│
├── logs/                     # Operation logs
│
├── models/                   # Data models
│   └── constants.py          # Generated constants
│
├── templates/                # Template files
│
├── README.md                 # This file
├── create_folder_structure.py # Setup script
├── generate_constants.py     # Constants generator
└── main.py                   # Main CLI entry point
```

## Data Formats

### JSON Format

```json
[
  {
    "type": "Test Case",
    "title": "Login Test",
    "description": "Verify login functionality",
    "test_steps": [
      {
        "action": "Navigate to login page",
        "expected": "Login page displays"
      },
      {
        "action": "Enter credentials",
        "expected": "User logged in"
      }
    ]
  }
]
```

### CSV Format

```
Type,Title,Description,StepAction1,StepExpected1,StepAction2,StepExpected2
Test Case,Login Test,Verify login,Navigate to login,Login page shows,Enter credentials,User logged in
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.