"""
Work Item operations for Azure DevOps.
Handles creation, updating, linking of work items like User Stories, Tasks, Bugs, etc.
"""
import sys
import os
import logging
import requests
from datetime import datetime
import html2text
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, WorkItem

# Import from project modules
sys.path.append("../")
from config.settings import AZURE_DEVOPS_PROJECT, AZURE_DEVOPS_ORG
from api.auth import get_connection

logger = logging.getLogger(__name__)

class WorkItemClient:
    """Client for managing Azure DevOps work items."""

    def __init__(self):
        """Initialize the work item client."""
        self.connection = get_connection()
        self.client = self.connection.clients.get_work_item_tracking_client()
        self.project = AZURE_DEVOPS_PROJECT
        self.org_url = AZURE_DEVOPS_ORG

    def create_work_item(self, work_item_type, title, description=None, assigned_to=None,
                        area_path=None, iteration_path=None, additional_fields=None):
        """
        Create a new work item.

        Args:
            work_item_type (str): Type of work item (e.g., 'Task', 'Bug', 'User Story')
            title (str): Title of the work item
            description (str, optional): Description of the work item
            assigned_to (str, optional): User to assign the work item to
            area_path (str, optional): Area path for the work item
            iteration_path (str, optional): Iteration path for the work item
            additional_fields (dict, optional): Additional fields to set on the work item

        Returns:
            WorkItem: The created work item
        """
        # Create document with work item field operations
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

        if assigned_to:
            document.append(
                JsonPatchOperation(
                    op='add',
                    path='/fields/System.AssignedTo',
                    value=assigned_to
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
            # Create the work item
            work_item = self.client.create_work_item(
                document=document,
                project=self.project,
                type=work_item_type
            )

            logger.info(f"Created {work_item_type} #{work_item.id}: {title}")
            return work_item

        except Exception as e:
            logger.error(f"Failed to create work item: {str(e)}")
            raise

    def update_work_item(self, work_item_id, updates, suppress_notifications=False):
        """
        Update an existing work item.

        Args:
            work_item_id (int): ID of the work item to update
            updates (dict): Dictionary of field paths and values to update
            suppress_notifications (bool, optional): Whether to suppress email notifications

        Returns:
            WorkItem: The updated work item
        """
        document = []

        # Create update operations for each field
        for field_path, value in updates.items():
            document.append(
                JsonPatchOperation(
                    op='add',
                    path=f'/fields/{field_path}',
                    value=value
                )
            )

        try:
            # Update the work item
            work_item = self.client.update_work_item(
                document=document,
                id=work_item_id,
                suppress_notifications=suppress_notifications
            )

            logger.info(f"Updated Work Item #{work_item_id}")
            return work_item

        except Exception as e:
            logger.error(f"Failed to update work item #{work_item_id}: {str(e)}")
            raise

    def get_work_item(self, work_item_id, expand="All"):
        """
        Retrieve a work item by ID.

        Args:
            work_item_id (int): ID of the work item to retrieve
            expand (str, optional): What to expand in the result. Options: None, Relations, Fields, Links, All

        Returns:
            WorkItem: The retrieved work item
        """
        try:
            work_item = self.client.get_work_item(id=work_item_id, expand=expand)
            return work_item

        except Exception as e:
            logger.error(f"Failed to retrieve work item #{work_item_id}: {str(e)}")
            raise

    def create_child_work_item(self, parent_id, work_item_type, title, description=None,
                              assigned_to=None, additional_fields=None):
        """
        Create a child work item linked to a parent.

        Args:
            parent_id (int): ID of the parent work item
            work_item_type (str): Type of work item to create
            title (str): Title of the work item
            description (str, optional): Description of the work item
            assigned_to (str, optional): User to assign the work item to
            additional_fields (dict, optional): Additional fields to set

        Returns:
            WorkItem: The created child work item
        """
        # Create the child work item first
        child = self.create_work_item(
            work_item_type=work_item_type,
            title=title,
            description=description,
            assigned_to=assigned_to,
            additional_fields=additional_fields
        )

        # Create the parent-child relationship
        relation_document = [
            JsonPatchOperation(
                op='add',
                path='/relations/-',
                value={
                    'rel': 'System.LinkTypes.Hierarchy-Reverse',
                    'url': f'{self.org_url}/{self.project}/_apis/wit/workItems/{parent_id}'
                }
            )
        ]

        try:
            # Update the child work item with the parent relationship
            updated_child = self.client.update_work_item(
                document=relation_document,
                id=child.id
            )

            logger.info(f"Created child work item #{child.id} under parent #{parent_id}")
            return updated_child

        except Exception as e:
            logger.error(f"Failed to create parent-child relationship: {str(e)}")
            # Try to delete the child work item to clean up
            try:
                self.client.delete_work_item(id=child.id)
            except:
                pass
            raise

    def get_user_story_details(self, user_story_id):
        """
        Get detailed information about a user story including acceptance criteria.

        Args:
            user_story_id (int): ID of the user story

        Returns:
            dict: Dictionary with user story details
        """
        try:
            # Get the work item
            work_item = self.get_work_item(user_story_id)

            # Extract the fields we're interested in
            fields = work_item.fields

            # Create a structured response
            details = {
                'id': work_item.id,
                'title': fields.get('System.Title', ''),
                'description': fields.get('System.Description', ''),
                'acceptance_criteria': fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', ''),
                'state': fields.get('System.State', ''),
                'assigned_to': fields.get('System.AssignedTo', ''),
                'area_path': fields.get('System.AreaPath', ''),
                'iteration_path': fields.get('System.IterationPath', ''),
                'created_date': fields.get('System.CreatedDate', ''),
                'created_by': fields.get('System.CreatedBy', ''),
                'changed_date': fields.get('System.ChangedDate', ''),
                'changed_by': fields.get('System.ChangedBy', '')
            }

            # Add any custom fields that might be present
            for field, value in fields.items():
                if field not in details.values():
                    details[field] = value

            logger.info(f"Retrieved user story #{user_story_id} details")
            return details

        except Exception as e:
            logger.error(f"Failed to get user story details for #{user_story_id}: {str(e)}")
            raise

    def create_bug_or_defect(self, item_type, title, description=None, steps_to_reproduce=None,
                             system_info=None, assigned_to=None, severity=None, priority=None,
                             area_path=None, iteration_path=None, additional_fields=None):
        """
        Create a new Bug or Defect work item.

        Args:
            item_type (str): Type of work item ('Bug' or 'Defect')
            title (str): Title of the bug/defect
            description (str, optional): Description of the bug/defect
            steps_to_reproduce (str, optional): Steps to reproduce the bug/defect
            system_info (str, optional): System information related to the bug/defect
            assigned_to (str, optional): User to assign the bug/defect to
            severity (str, optional): Severity level (e.g., '1 - Critical', '2 - High')
            priority (int, optional): Priority level (e.g., 1, 2)
            area_path (str, optional): Area path for the bug/defect
            iteration_path (str, optional): Iteration path for the bug/defect
            additional_fields (dict, optional): Additional fields to set

        Returns:
            WorkItem: The created bug/defect
        """
        # Prepare fields
        fields = {}

        if additional_fields:
            fields.update(additional_fields)

        if steps_to_reproduce:
            fields['Microsoft.VSTS.TCM.ReproSteps'] = steps_to_reproduce

        if system_info:
            fields['Microsoft.VSTS.TCM.SystemInfo'] = system_info

        if severity:
            fields['Microsoft.VSTS.Common.Severity'] = severity

        if priority:
            fields['Microsoft.VSTS.Common.Priority'] = priority

        # Create the bug/defect
        item = self.create_work_item(
            work_item_type=item_type,
            title=title,
            description=description,
            assigned_to=assigned_to,
            area_path=area_path,
            iteration_path=iteration_path,
            additional_fields=fields
        )

        logger.info(f"Created {item_type} #{item.id}: {title}")
        return item


    def bulk_create_tasks(self, parent_id, tasks):
        """
        Create multiple tasks under a parent work item.

        Args:
            parent_id (int): ID of the parent work item
            tasks (list): List of task dictionaries, each containing:
                - title (str): Task title
                - description (str, optional): Task description
                - assigned_to (str, optional): User to assign the task to
                - additional_fields (dict, optional): Additional fields

        Returns:
            list: List of created task work items
        """
        created_tasks = []

        try:
            # Create each task
            for task_data in tasks:
                # Extract task data
                title = task_data.get('title')
                description = task_data.get('description')
                assigned_to = task_data.get('assigned_to')
                additional_fields = task_data.get('additional_fields', {})

                # Create the child task
                task = self.create_child_work_item(
                    parent_id=parent_id,
                    work_item_type='Task',
                    title=title,
                    description=description,
                    assigned_to=assigned_to,
                    additional_fields=additional_fields
                )

                created_tasks.append(task)

            logger.info(f"Created {len(created_tasks)} tasks under parent #{parent_id}")
            return created_tasks

        except Exception as e:
            logger.error(f"Failed to bulk create tasks under parent #{parent_id}: {str(e)}")
            raise

    def export_work_item_details(self, work_item_id):
        """
        Export a work item's metadata and attachments to /WorkItem/<id>/ folder.

        Args:
            work_item_id (int): ID of the work item

        Returns:
            str: Path to the folder containing the exported work item details
        """
        try:
            # Get full work item including attachments
            work_item = self.get_work_item(work_item_id, expand="All")
            fields = work_item.fields

            # Create HTML to text converter for cleaning HTML content
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False

            # Folder setup - create at project root
            base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "WorkItem")
            ticket_folder = os.path.join(base_path, str(work_item_id))
            os.makedirs(ticket_folder, exist_ok=True)

            # Extract basic info
            work_item_type = fields.get("System.WorkItemType", "Unknown")
            title = fields.get("System.Title", "")
            description = fields.get("System.Description", "")
            if description:
                # Convert HTML to markdown/text
                description = h.handle(description)

            state = fields.get("System.State", "Unknown")

            # Get additional fields based on work item type
            additional_content = ""

            if work_item_type == "User Story":
                # Get acceptance criteria
                acceptance_criteria = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", "")
                if acceptance_criteria:
                    acceptance_criteria = h.handle(acceptance_criteria)
                additional_content += "\n\nAcceptance Criteria:\n" + (acceptance_criteria if acceptance_criteria else "N/A")

                # Get value area and business value if available
                value_area = fields.get("Microsoft.VSTS.Common.ValueArea", "")
                business_value = fields.get("Microsoft.VSTS.Common.BusinessValue", "")
                if value_area:
                    additional_content += f"\n\nValue Area: {value_area}"
                if business_value:
                    additional_content += f"\nBusiness Value: {business_value}"

            elif work_item_type == "Bug":
                # Get repro steps, system info, and severity
                repro_steps = fields.get("Microsoft.VSTS.TCM.ReproSteps", "")
                if repro_steps:
                    repro_steps = h.handle(repro_steps)
                system_info = fields.get("Microsoft.VSTS.TCM.SystemInfo", "")
                severity = fields.get("Microsoft.VSTS.Common.Severity", "")
                priority = fields.get("Microsoft.VSTS.Common.Priority", "")

                additional_content += "\n\nSteps to Reproduce:\n" + (repro_steps if repro_steps else "N/A")
                if system_info:
                    additional_content += f"\n\nSystem Info:\n{system_info}"
                if severity:
                    additional_content += f"\n\nSeverity: {severity}"
                if priority:
                    additional_content += f"\nPriority: {priority}"

            # Get common fields for all work item types
            assigned_to = fields.get("System.AssignedTo", {})
            assigned_to_name = assigned_to.get('displayName', '') if isinstance(assigned_to, dict) else assigned_to

            created_date = fields.get("System.CreatedDate", "")
            created_by = fields.get("System.CreatedBy", {})
            created_by_name = created_by.get('displayName', '') if isinstance(created_by, dict) else created_by

            changed_date = fields.get("System.ChangedDate", "")
            changed_by = fields.get("System.ChangedBy", {})
            changed_by_name = changed_by.get('displayName', '') if isinstance(changed_by, dict) else changed_by

            # Format dates if they exist
            if created_date:
                try:
                    created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            if changed_date:
                try:
                    changed_date = datetime.fromisoformat(changed_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # Write main details file
            with open(os.path.join(ticket_folder, "details.txt"), "w", encoding="utf-8") as f:
                f.write(f"Work Item ID: {work_item_id}\n")
                f.write(f"Work Item Type: {work_item_type}\n")
                f.write(f"Title: {title}\n")
                f.write(f"State: {state}\n")

                if assigned_to_name:
                    f.write(f"Assigned To: {assigned_to_name}\n")

                f.write(f"Area Path: {fields.get('System.AreaPath', 'N/A')}\n")
                f.write(f"Iteration Path: {fields.get('System.IterationPath', 'N/A')}\n")

                if created_date:
                    f.write(f"Created Date: {created_date}\n")
                if created_by_name:
                    f.write(f"Created By: {created_by_name}\n")
                if changed_date:
                    f.write(f"Last Modified Date: {changed_date}\n")
                if changed_by_name:
                    f.write(f"Last Modified By: {changed_by_name}\n")

                f.write("\n\nDescription:\n")
                f.write(description if description else "N/A")

                # Add type-specific additional content
                f.write(additional_content)

                # Add all remaining fields
                f.write("\n\nAll Fields:\n")
                for field_name, field_value in fields.items():
                    # Skip fields that are complex objects or we've already handled
                    if isinstance(field_value, (dict, list)) or "System." in field_name or "Microsoft.VSTS" in field_name:
                        continue
                    f.write(f"{field_name}: {field_value}\n")

            # Download attachments (if any)
            attachments_found = False
            if hasattr(work_item, "relations") and work_item.relations:
                for rel in work_item.relations:
                    if rel.rel == "AttachedFile":
                        attachments_found = True
                        attachment_url = rel.url
                        file_name = rel.attributes.get("name", f"attachment_{work_item_id}")

                        # Create attachment folder if this is the first attachment
                        attachments_folder = os.path.join(ticket_folder, "attachments")
                        if not os.path.exists(attachments_folder):
                            os.makedirs(attachments_folder, exist_ok=True)

                        # Use authorization from the connection
                        auth_header = {"Authorization": f"Basic {self.connection._creds._password}"}

                        response = requests.get(attachment_url, headers=auth_header)
                        if response.ok:
                            with open(os.path.join(attachments_folder, file_name), "wb") as f:
                                f.write(response.content)
                            logger.info(f"Downloaded attachment '{file_name}' for work item #{work_item_id}")
                        else:
                            logger.warning(f"Failed to download attachment '{file_name}' for work item #{work_item_id}. Status: {response.status_code}")

            if not attachments_found:
                logger.info(f"No attachments found for work item #{work_item_id}")

            # Get relationships and create a links.txt file
            has_links = False
            if hasattr(work_item, "relations") and work_item.relations:
                links_data = []

                for rel in work_item.relations:
                    # Skip attachments as we've handled them separately
                    if rel.rel == "AttachedFile":
                        continue

                    has_links = True
                    rel_type = rel.rel.split('.')[-1]  # Get the last part of the relationship type

                    # Try to extract the target work item ID from the URL
                    target_id = "Unknown"
                    if "workItems/" in rel.url:
                        target_id = rel.url.split("workItems/")[-1]

                    links_data.append({
                        "type": rel_type,
                        "target_id": target_id,
                        "url": rel.url,
                        "attributes": rel.attributes
                    })

                if has_links:
                    with open(os.path.join(ticket_folder, "links.txt"), "w", encoding="utf-8") as f:
                        f.write(f"Work Item #{work_item_id} Links:\n\n")

                        for link in links_data:
                            f.write(f"Type: {link['type']}\n")
                            f.write(f"Target ID: {link['target_id']}\n")
                            f.write(f"URL: {link['url']}\n")

                            # Write attributes if available
                            if link['attributes']:
                                f.write("Attributes:\n")
                                for key, value in link['attributes'].items():
                                    f.write(f"  {key}: {value}\n")

                            f.write("\n")

            logger.info(f"Exported work item #{work_item_id} to {ticket_folder}")

            # Return the path to the exported folder
            return ticket_folder

        except Exception as e:
            logger.error(f"Failed to export work item #{work_item_id}: {str(e)}")
            raise