"""
Work Item operations for Azure DevOps.
Handles creation, updating, and linking of work items like User Stories, Tasks, Bugs, etc.
"""
import sys
import logging
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
        connection = get_connection()
        self.client = connection.clients.get_work_item_tracking_client()
        self.project = AZURE_DEVOPS_PROJECT
    
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
                    'url': f'{AZURE_DEVOPS_ORG}/{self.project}/_apis/wit/workItems/{parent_id}'
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
    
    def create_bug(self, title, description=None, steps_to_reproduce=None, assigned_to=None, 
                  severity=None, priority=None, area_path=None, iteration_path=None, additional_fields=None):
        """
        Create a new bug.
        
        Args:
            title (str): Title of the bug
            description (str, optional): Description of the bug
            steps_to_reproduce (str, optional): Steps to reproduce the bug
            assigned_to (str, optional): User to assign the bug to
            severity (str, optional): Severity level (e.g., '1 - Critical', '2 - High')
            priority (int, optional): Priority level (e.g., 1, 2)
            area_path (str, optional): Area path for the bug
            iteration_path (str, optional): Iteration path for the bug
            additional_fields (dict, optional): Additional fields to set
            
        Returns:
            WorkItem: The created bug
        """
        # Prepare fields
        fields = {}
        
        if additional_fields:
            fields.update(additional_fields)
        
        if steps_to_reproduce:
            # If steps_to_reproduce is provided, add it to the description or to Microsoft.VSTS.TCM.ReproSteps
            fields['Microsoft.VSTS.TCM.ReproSteps'] = steps_to_reproduce
        
        if severity:
            fields['Microsoft.VSTS.Common.Severity'] = severity
        
        if priority:
            fields['Microsoft.VSTS.Common.Priority'] = priority
        
        # Create the bug
        bug = self.create_work_item(
            work_item_type='Bug',
            title=title,
            description=description,
            assigned_to=assigned_to,
            area_path=area_path,
            iteration_path=iteration_path,
            additional_fields=fields
        )
        
        logger.info(f"Created Bug #{bug.id}: {title}")
        return bug
    
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