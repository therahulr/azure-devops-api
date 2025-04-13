"""
File: azure-devops-api/api/test_cases.py
Test case management operations for Azure DevOps.
"""
import sys
import logging
import requests
import xml.etree.ElementTree as ET
import time
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

# Import from project modules
sys.path.append("../")
from config.settings import AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_ORG, AZURE_DEVOPS_API_VERSION, AZURE_DEVOPS_PAT
from api.auth import get_connection

logger = logging.getLogger(__name__)

class TestCaseClient:
    """Client for managing Azure DevOps test cases."""

    def __init__(self):
        """Initialize the test case client."""
        connection = get_connection()
        self.wit_client = connection.clients.get_work_item_tracking_client()
        # For direct REST API calls that might not be supported in SDK
        self.test_client = connection.clients.get_test_client()
        self.project = AZURE_DEVOPS_PROJECT
        self.org_url = AZURE_DEVOPS_ORG
        self.api_version = AZURE_DEVOPS_API_VERSION
        self.pat = AZURE_DEVOPS_PAT

    def create_test_case(self, title, description=None, area_path=None, iteration_path=None,
                         test_steps=None, automation_status=None, additional_fields=None):
        """
        Create a new test case with optional test steps.

        Args:
            title (str): Title of the test case
            description (str, optional): Description of the test case
            area_path (str, optional): Area path for the test case
            iteration_path (str, optional): Iteration path for the test case
            test_steps (list, optional): List of test steps (dicts with 'action' and 'expected' keys)
            automation_status (str, optional): Automation status (e.g., 'Not Automated', 'Automated')
            additional_fields (dict, optional): Additional fields to set

        Returns:
            WorkItem: The created test case
        """
        # Create document with test case field operations
        document = [
            JsonPatchOperation(
                op='add',
                path='/fields/System.Title',
                value=title
            )
        ]

        # Add optional fields if provided
        if description:
            document.append(
                JsonPatchOperation(
                    op='add',
                    path='/fields/System.Description',
                    value=description
                )
            )

        if area_path:
            document.append(
                JsonPatchOperation(
                    op='add',
                    path='/fields/System.AreaPath',
                    value=area_path
                )
            )

        if iteration_path:
            document.append(
                JsonPatchOperation(
                    op='add',
                    path='/fields/System.IterationPath',
                    value=iteration_path
                )
            )

        if automation_status:
            document.append(
                JsonPatchOperation(
                    op='add',
                    path='/fields/Microsoft.VSTS.TCM.AutomationStatus',
                    value=automation_status
                )
            )

        # Add any additional fields
        if additional_fields:
            for field, value in additional_fields.items():
                document.append(
                    JsonPatchOperation(
                        op='add',
                        path=f'/fields/{field}',
                        value=value
                    )
                )

        try:
            # Create the test case work item
            test_case = self.wit_client.create_work_item(
                document=document,
                project=self.project,
                type='Test Case'
            )

            logger.info(f"Created Test Case #{test_case.id}: {title}")

            # Add test steps if provided
            if test_steps:
                updated_case = self.update_test_steps(test_case.id, test_steps)

                # Get the updated test case with all information
                return self.wit_client.get_work_item(id=test_case.id, expand='All')

            return test_case

        except Exception as e:
            logger.error(f"Failed to create test case: {str(e)}")
            raise

    def build_test_steps_xml(self, test_steps, starting_id=1):
        """
        Build the correct XML structure for Azure DevOps test steps using parameterizedString.

        Args:
            test_steps (list): List of dictionaries with 'action' and 'expected' keys
            starting_id (int): Starting step ID, useful when appending steps

        Returns:
            str: XML string with formatted steps
        """
        root = ET.Element("steps", id="0", last=str(starting_id + len(test_steps) - 1))

        for index, step in enumerate(test_steps, start=starting_id):
            step_elem = ET.SubElement(root, "step", id=str(index), type="ActionStep")

            action_elem = ET.SubElement(step_elem, "parameterizedString", {"isformatted": "true", "type": "plaintext"})
            action_elem.text = step.get("action", "")

            expected_elem = ET.SubElement(step_elem, "parameterizedString",
                                          {"isformatted": "true", "type": "plaintext"})
            expected_elem.text = step.get("expected", "")

        return ET.tostring(root, encoding="unicode")

    def add_test_steps(self, test_case_id, test_steps):
        try:
            # Get current steps XML
            test_case = self.wit_client.get_work_item(id=test_case_id)
            current_steps_xml = test_case.fields.get("Microsoft.VSTS.TCM.Steps", "")

            if current_steps_xml:
                root = ET.fromstring(current_steps_xml)
                existing_step_ids = [int(s.get("id", 0)) for s in root.findall(".//step")]
                highest_id = max(existing_step_ids) if existing_step_ids else 0
            else:
                highest_id = 0

            steps_xml = self.build_test_steps_xml(test_steps, starting_id=highest_id + 1)

            document = [
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.TCM.Steps",
                    value=steps_xml
                )
            ]

            updated_test_case = self.wit_client.update_work_item(
                document=document,
                id=test_case_id
            )

            self._ensure_steps_are_visible(test_case_id)

            logger.info(f"Added {len(test_steps)} test steps to Test Case #{test_case_id}")
            return updated_test_case

        except Exception as e:
            logger.error(f"Failed to add test steps: {str(e)}")
            raise

    def update_test_steps(self, test_case_id, test_steps):
        try:
            steps_xml = self.build_test_steps_xml(test_steps)

            document = [
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.TCM.Steps",
                    value=steps_xml
                )
            ]

            updated_test_case = self.wit_client.update_work_item(
                document=document,
                id=test_case_id
            )

            self._ensure_steps_are_visible(test_case_id)

            logger.info(f"Updated test steps for Test Case #{test_case_id}")
            return updated_test_case

        except Exception as e:
            logger.error(f"Failed to update test steps for test case #{test_case_id}: {str(e)}")
            raise

    def _ensure_steps_are_visible(self, test_case_id):
        """
        Ensure test steps are visible by making a state change and then reverting it.
        This forces Azure DevOps to refresh the test steps UI.

        Args:
            test_case_id (int): ID of the test case
        """
        try:
            # Get the current test case to see its state
            test_case = self.wit_client.get_work_item(id=test_case_id)
            current_state = test_case.fields.get('System.State', 'Design')

            # Determine a temporary state to switch to
            temp_state = 'Ready' if current_state != 'Ready' else 'Design'

            # Change to temporary state
            document = [
                JsonPatchOperation(
                    op='add',
                    path='/fields/System.State',
                    value=temp_state
                )
            ]

            self.wit_client.update_work_item(
                document=document,
                id=test_case_id
            )

            # Wait briefly
            time.sleep(1)

            # Change back to original state
            document = [
                JsonPatchOperation(
                    op='add',
                    path='/fields/System.State',
                    value=current_state
                )
            ]

            self.wit_client.update_work_item(
                document=document,
                id=test_case_id
            )

            logger.debug(f"Forced step visibility for Test Case #{test_case_id}")

        except Exception as e:
            logger.warning(f"Failed to ensure step visibility for test case #{test_case_id}: {str(e)}")
            # We don't want to raise an exception here as it's just a helper method
    
    def get_test_plans(self):
        """
        Get all test plans in the project.
        
        Returns:
            list: List of test plans
        """
        try:
            # Use the test client to get test plans
            plans = self.test_client.get_plans(project=self.project)
            return plans
        except Exception as e:
            logger.error(f"Failed to get test plans: {str(e)}")
            raise

    def get_test_suites(self, plan_id):
        """
        Get all test suites in a test plan.
        
        Args:
            plan_id (int): ID of the test plan
            
        Returns:
            list: List of test suites
        """
        try:
            # Use the test client to get test suites
            suites = self.test_client.get_test_suites_for_plan(
                project=self.project,
                plan_id=plan_id
            )
            return suites
        except Exception as e:
            logger.error(f"Failed to get test suites for plan {plan_id}: {str(e)}")
            raise

    def get_test_cases_in_suite(self, plan_id, suite_id):
        """
        Get all test cases in a test suite.
        
        Args:
            plan_id (int): ID of the test plan
            suite_id (int): ID of the test suite
            
        Returns:
            list: List of test cases
        """
        try:
            # Use the test client to get test cases
            test_cases = self.test_client.get_test_cases(
                project=self.project,
                plan_id=plan_id,
                suite_id=suite_id
            )
            return test_cases
        except Exception as e:
            logger.error(f"Failed to get test cases for suite {suite_id} in plan {plan_id}: {str(e)}")
            raise

    def add_test_case_to_suite(self, plan_id, suite_id, test_case_id):
        """
        Add a test case to a test suite.
        
        Args:
            plan_id (int): ID of the test plan
            suite_id (int): ID of the test suite
            test_case_id (int): ID of the test case
            
        Returns:
            dict: Result of the operation
        """
        # For this operation, we need to use direct REST API call
        url = f"{self.org_url}/{self.project}/_apis/test/plans/{plan_id}/suites/{suite_id}/testcases/{test_case_id}?api-version={self.api_version}"
        
        # Create auth header
        auth_header = requests.auth.HTTPBasicAuth('', self.pat)
        
        try:
            response = requests.post(url, auth=auth_header)
            response.raise_for_status()
            
            logger.info(f"Added test case #{test_case_id} to suite {suite_id} in plan {plan_id}")
            return response.json()
        
        except Exception as e:
            logger.error(f"Failed to add test case #{test_case_id} to suite: {str(e)}")
            raise