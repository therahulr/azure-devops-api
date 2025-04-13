#!/usr/bin/env python
"""
Script to generate Azure DevOps constants from the current project configuration.
This populates the models/constants.py file with work item types, area paths, and iteration paths
specific to your Azure DevOps project.
"""
import os
import sys
import logging
import re
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Import project modules
from api.auth import get_connection
from api.azure_devops_core_queries import AzureDevOpsCoreQueries
from config.settings import AZURE_DEVOPS_PROJECT

def clean_name_for_constant(name):
    """
    Convert a name to a valid Python constant name.
    
    Args:
        name (str): The name to convert
        
    Returns:
        str: Valid Python constant name (UPPER_SNAKE_CASE)
    """
    # Replace spaces, dots, and special characters with underscores
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name)
    
    # Ensure it starts with a letter
    if re.match(r'^[0-9]', clean):
        clean = f"_{clean}"
    
    # Convert to uppercase
    return clean.upper()

def get_constants_file_path():
    """Get the path to the constants.py file."""
    return Path(__file__).parent / 'models' / 'constants.py'

def generate_work_item_type_constants(client):
    """
    Generate constants for work item types.
    
    Args:
        client (AzureDevOpsCoreQueries): The Azure DevOps client
        
    Returns:
        tuple: (python_code, dict_of_values)
    """
    try:
        work_item_types = client.get_work_item_types()
        
        code_lines = ["class WorkItemType:"]
        code_lines.append('    """Constants for work item types."""')
        
        values_dict = {}
        
        for wit in work_item_types:
            name = wit['name']
            reference_name = wit['reference_name']
            constant_name = clean_name_for_constant(name)
            
            # Store in dict for later use
            values_dict[constant_name] = reference_name
            
            # Add to code
            code_lines.append(f"    {constant_name} = \"{reference_name}\"")
        
        return "\n".join(code_lines), values_dict
    
    except Exception as e:
        logger.error(f"Failed to generate work item type constants: {str(e)}")
        return "class WorkItemType:\n    pass", {}

def generate_area_path_constants(client):
    """
    Generate constants for area paths.
    
    Args:
        client (AzureDevOpsCoreQueries): The Azure DevOps client
        
    Returns:
        tuple: (python_code, dict_of_values)
    """
    try:
        area_paths = client.get_area_paths()
        
        code_lines = ["class AreaPath:"]
        code_lines.append('    """Constants for area paths."""')
        
        values_dict = {}
        
        # Helper function to process the area paths recursively
        def process_area_paths(node, prefix=""):
            node_path = node['path']
            
            # Skip the root node in the constant name
            if prefix:
                # Generate a constant name for the current node
                constant_name = clean_name_for_constant(prefix + node['name'])
                
                # Store in dict for later use
                values_dict[constant_name] = node_path
                
                # Add to code
                code_lines.append(f"    {constant_name} = \"{node_path}\"")
            
            # Process children
            if node.get('children'):
                new_prefix = node['name'] + "\\" if not prefix else prefix + node['name'] + "\\"
                for child in node['children']:
                    process_area_paths(child, new_prefix)
        
        # Start processing from the root
        process_area_paths(area_paths)
        
        return "\n".join(code_lines), values_dict
    
    except Exception as e:
        logger.error(f"Failed to generate area path constants: {str(e)}")
        return "class AreaPath:\n    pass", {}

def generate_iteration_path_constants(client):
    """
    Generate constants for iteration paths.
    
    Args:
        client (AzureDevOpsCoreQueries): The Azure DevOps client
        
    Returns:
        tuple: (python_code, dict_of_values)
    """
    try:
        iteration_paths = client.get_iteration_paths()
        
        code_lines = ["class IterationPath:"]
        code_lines.append('    """Constants for iteration paths."""')
        
        values_dict = {}
        
        # Helper function to process the iteration paths recursively
        def process_iteration_paths(node, prefix=""):
            node_path = node['path']
            
            # Skip the root node in the constant name
            if prefix:
                # Generate a constant name for the current node
                constant_name = clean_name_for_constant(prefix + node['name'])
                
                # Store in dict for later use
                values_dict[constant_name] = node_path
                
                # Add to code
                code_lines.append(f"    {constant_name} = \"{node_path}\"")
            
            # Process children
            if node.get('children'):
                new_prefix = node['name'] + "\\" if not prefix else prefix + node['name'] + "\\"
                for child in node['children']:
                    process_iteration_paths(child, new_prefix)
        
        # Start processing from the root
        process_iteration_paths(iteration_paths)
        
        return "\n".join(code_lines), values_dict
    
    except Exception as e:
        logger.error(f"Failed to generate iteration path constants: {str(e)}")
        return "class IterationPath:\n    pass", {}

def include_static_constants():
    """
    Include static constants that don't need to be fetched from Azure DevOps.
    
    Returns:
        str: Python code for static constants
    """
    field_constants = """class Field:
    \"""Constants for fields.\"""
    # System fields
    ID = "System.Id"
    TITLE = "System.Title"
    DESCRIPTION = "System.Description"
    ASSIGNED_TO = "System.AssignedTo"
    STATE = "System.State"
    REASON = "System.Reason"
    CREATED_BY = "System.CreatedBy"
    CREATED_DATE = "System.CreatedDate"
    CHANGED_BY = "System.ChangedBy"
    CHANGED_DATE = "System.ChangedDate"
    AREA_PATH = "System.AreaPath"
    ITERATION_PATH = "System.IterationPath"
    WORK_ITEM_TYPE = "System.WorkItemType"
    TAGS = "System.Tags"
    
    # Microsoft VSTS fields
    PRIORITY = "Microsoft.VSTS.Common.Priority"
    SEVERITY = "Microsoft.VSTS.Common.Severity"
    VALUE_AREA = "Microsoft.VSTS.Common.ValueArea"
    BUSINESS_VALUE = "Microsoft.VSTS.Common.BusinessValue"
    TIME_CRITICALITY = "Microsoft.VSTS.Common.TimeCriticality"
    RISK = "Microsoft.VSTS.Common.Risk"
    EFFORT = "Microsoft.VSTS.Scheduling.Effort"
    ORIGINAL_ESTIMATE = "Microsoft.VSTS.Scheduling.OriginalEstimate"
    REMAINING_WORK = "Microsoft.VSTS.Scheduling.RemainingWork"
    COMPLETED_WORK = "Microsoft.VSTS.Scheduling.CompletedWork"
    
    # User Story specific fields
    ACCEPTANCE_CRITERIA = "Microsoft.VSTS.Common.AcceptanceCriteria"
    
    # Test case specific fields
    TEST_STEPS = "Microsoft.VSTS.TCM.Steps"
    AUTOMATION_STATUS = "Microsoft.VSTS.TCM.AutomationStatus"
"""

    link_type_constants = """class LinkType:
    \"""Constants for link types.\"""
    # Hierarchy links
    PARENT = "System.LinkTypes.Hierarchy-Reverse"
    CHILD = "System.LinkTypes.Hierarchy-Forward"
    
    # Related links
    RELATED = "System.LinkTypes.Related"
    
    # Dependency links
    PREDECESSOR = "System.LinkTypes.Dependency-Reverse"
    SUCCESSOR = "System.LinkTypes.Dependency-Forward"
    
    # Test links
    TESTED_BY = "Microsoft.VSTS.Common.TestedBy-Forward"
    TESTS = "Microsoft.VSTS.Common.TestedBy-Reverse"
    
    # File links
    ATTACHED_FILE = "AttachedFile"
    
    # External links
    HYPERLINK = "Hyperlink"
"""
    
    return field_constants + "\n" + link_type_constants

def main():
    """Main function to generate constants."""
    try:
        # Establish connection
        connection = get_connection()
        
        # Create the client
        client = AzureDevOpsCoreQueries(
            connection=connection,
            project=AZURE_DEVOPS_PROJECT
        )
        
        # Generate constants
        wit_constants, wit_values = generate_work_item_type_constants(client)
        area_constants, area_values = generate_area_path_constants(client)
        iteration_constants, iteration_values = generate_iteration_path_constants(client)
        static_constants = include_static_constants()
        
        # Create the constants file content
        file_content = f'''"""
Constants for Azure DevOps work items.
This file is auto-generated by the generate_constants.py script.
Do not modify directly - your changes would be overwritten.
"""

{wit_constants}

{area_constants}

{iteration_constants}

{static_constants}
'''
        
        # Write to file
        constants_file = get_constants_file_path()
        with open(constants_file, 'w') as f:
            f.write(file_content)
        
        logger.info(f"Constants file generated successfully at {constants_file}")
        
        # Summary
        print(f"Generated constants:")
        print(f"- {len(wit_values)} Work Item Types")
        print(f"- {len(area_values)} Area Paths")
        print(f"- {len(iteration_values)} Iteration Paths")
        print(f"- Static Field and Link Type constants")
        print(f"\nConstants file written to: {constants_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate constants: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())