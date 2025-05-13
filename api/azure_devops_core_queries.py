"""
Azure DevOps API - Core Operations Module
Handles basic fetching operations for work item types, areas, sprints, and work item details.

This module integrates with the existing authentication and project structure.
"""
import logging
import sys
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AzureDevOpsCoreQueries:
    """Client for Azure DevOps core query operations."""
    
    def __init__(self, connection, project):
        """
        Initialize the Azure DevOps client.
        
        Args:
            connection: Authenticated Azure DevOps connection
            project (str): Azure DevOps project name
        """
        self.project = project
        
        # Get clients for different services
        self.wit_client = connection.clients.get_work_item_tracking_client()
        self.work_client = connection.clients.get_work_client()
        self.core_client = connection.clients.get_core_client()
        
        logger.info(f"Initialized Azure DevOps Core Queries for project: {project}")

    # 1st function - Get all work item types

    def get_work_item_types(self):
        """
        Get all work item types defined in the project.
        
        Returns:
            list: List of work item type objects with names and references
        """
        try:
            work_item_types = self.wit_client.get_work_item_types(self.project)
            
            # Extract relevant information for easier use
            types_info = []
            for wit in work_item_types:
                types_info.append({
                    'name': wit.name,
                    'reference_name': wit.reference_name,
                    'description': wit.description,
                    'icon': wit.icon
                })
            
            logger.info(f"Retrieved {len(work_item_types)} work item types from project {self.project}")
            return types_info
        except Exception as e:
            logger.error(f"Failed to get work item types: {str(e)}")
            raise


    # 2nd function - Get all area paths
    def list_all_area_paths(self):
        """
        Recursively print all area paths defined in the project.
        """
        try:
            # Retrieve the root node for area classifications
            root = self.wit_client.get_classification_node(
                project=self.project,
                structure_group='areas',
                path='',
                depth=20
            )

            area_paths = []

            def traverse(node, path):
                full_path = f"{path}\\{node.name}" if path else node.name
                area_paths.append(full_path)
                if hasattr(node, 'children') and node.children:
                    for child in node.children:
                        traverse(child, full_path)

            traverse(root, "")
            print("\nAvailable Area Paths:")
            for path in area_paths:
                print(f"- {path}")
            return area_paths
        except Exception as e:
            logger.error(f"Failed to fetch area paths: {str(e)}")
            raise

    # 3rd function - Get all iteration paths
    def get_iteration_paths(self):
        """
        Get all iteration paths (sprints) defined in the project.

        Returns:
            dict: Dictionary containing iteration paths structure
        """
        try:
            # Correct usage: get the root node of the iterations structure
            root = self.wit_client.get_classification_node(
                project=self.project,
                structure_group='iterations',
                path='',
                depth=20
            )

            def process_node(node, parent_path=""):
                current_path = f"{parent_path}\\{node.name}" if parent_path else node.name
                result = {
                    'name': node.name,
                    'path': current_path,
                    'id': node.id
                }

                # Extract start/finish dates if available
                if hasattr(node, 'attributes') and node.attributes:
                    if 'startDate' in node.attributes:
                        result['start_date'] = node.attributes['startDate']
                    if 'finishDate' in node.attributes:
                        result['finish_date'] = node.attributes['finishDate']

                # Recursively process children
                if hasattr(node, 'children') and node.children:
                    result['children'] = [process_node(child, current_path) for child in node.children]
                else:
                    result['children'] = []

                return result

            processed_iterations = process_node(root)
            logger.info(f"Retrieved iteration paths from project {self.project}")
            return processed_iterations

        except Exception as e:
            logger.error(f"Failed to get iteration paths: {str(e)}")
            raise

    # 4th function - Get work item details
    def get_work_item(self, work_item_id, expand="All"):
        """
        Get details of a specific work item.
        
        Args:
            work_item_id (int): ID of the work item to retrieve
            expand (str, optional): What to expand in the result. Options: None, Relations, Fields, Links, All
            
        Returns:
            dict: The retrieved work item data in a more accessible format
        """
        try:
            work_item = self.wit_client.get_work_item(id=work_item_id, expand=expand)
            
            # Process the work item for more accessible data
            result = {
                'id': work_item.id,
                'rev': work_item.rev,
                'url': work_item.url,
                'fields': {}
            }
            
            # Extract fields
            if hasattr(work_item, 'fields'):
                for field_name, field_value in work_item.fields.items():
                    result['fields'][field_name] = field_value
            
            # Extract relations if available
            if hasattr(work_item, 'relations') and work_item.relations:
                result['relations'] = []
                for relation in work_item.relations:
                    relation_info = {
                        'rel': relation.rel,
                        'url': relation.url
                    }
                    if hasattr(relation, 'attributes') and relation.attributes:
                        relation_info['attributes'] = relation.attributes
                    result['relations'].append(relation_info)
            
            logger.info(f"Retrieved work item #{work_item_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get work item #{work_item_id}: {str(e)}")
            raise

    # 5th function - Get multiple work items
    def get_work_items(self, work_item_ids, expand="All"):
        """
        Get details of multiple work items in a batch request.
        
        Args:
            work_item_ids (list): List of work item IDs to retrieve
            expand (str, optional): What to expand in the result. Options: None, Relations, Fields, Links, All
            
        Returns:
            list: List of retrieved work item objects in a more accessible format
        """
        if not work_item_ids:
            logger.warning("No work item IDs provided")
            return []
        
        try:
            # Split into batches of 200 (API limitation)
            batch_size = 200
            all_work_items = []
            
            for i in range(0, len(work_item_ids), batch_size):
                batch_ids = work_item_ids[i:i+batch_size]
                work_items_batch = self.wit_client.get_work_items(ids=batch_ids, expand=expand)
                
                # Process each work item
                for work_item in work_items_batch:
                    processed_item = {
                        'id': work_item.id,
                        'rev': work_item.rev,
                        'url': work_item.url,
                        'fields': {}
                    }
                    
                    # Extract fields
                    if hasattr(work_item, 'fields'):
                        for field_name, field_value in work_item.fields.items():
                            processed_item['fields'][field_name] = field_value
                    
                    # Extract relations if available
                    if hasattr(work_item, 'relations') and work_item.relations:
                        processed_item['relations'] = []
                        for relation in work_item.relations:
                            relation_info = {
                                'rel': relation.rel,
                                'url': relation.url
                            }
                            if hasattr(relation, 'attributes') and relation.attributes:
                                relation_info['attributes'] = relation.attributes
                            processed_item['relations'].append(relation_info)
                    
                    all_work_items.append(processed_item)
            
            logger.info(f"Retrieved {len(all_work_items)} work items")
            return all_work_items
        except Exception as e:
            logger.error(f"Failed to get work items: {str(e)}")
            raise
    
    def query_work_items(self, query_string):
        """
        Execute a WIQL query to find work items.
        
        Args:
            query_string (str): The WIQL query string 
            
        Returns:
            tuple: (work_item_references, query_result)
                - work_item_references: List of WorkItemReference objects with ID and URL
                - query_result: Full query result object
        """
        try:
            # Create the WIQL object
            wiql = Wiql(query=query_string)
            
            # Execute the query
            query_result = self.wit_client.query_by_wiql(wiql)
            
            # Get the work item references
            work_item_references = query_result.work_items
            
            logger.info(f"Query returned {len(work_item_references)} work items")
            return work_item_references, query_result
        except Exception as e:
            logger.error(f"Failed to execute WIQL query: {str(e)}")
            raise
    
    def get_queried_work_items(self, query_string, expand="All"):
        """
        Execute a WIQL query and return the full work item details.
        
        Args:
            query_string (str): The WIQL query string
            expand (str, optional): What to expand in the result. Options: None, Relations, Fields, Links, All
            
        Returns:
            list: List of work item objects with full details
        """
        try:
            # First get the work item references from the query
            work_item_references, _ = self.query_work_items(query_string)
            
            if not work_item_references:
                logger.info("Query returned no work items")
                return []
            
            # Extract the IDs
            work_item_ids = [int(reference.id) for reference in work_item_references]
            
            # Get the full work item details
            return self.get_work_items(work_item_ids, expand=expand)
        except Exception as e:
            logger.error(f"Failed to get queried work items: {str(e)}")
            raise
    
    def get_field_definitions(self):
        """
        Get all field definitions available in the organization.
        
        Returns:
            list: List of field definition objects
        """
        try:
            fields = self.wit_client.get_fields()
            
            # Process fields for easier consumption
            field_info = []
            for field in fields:
                field_info.append({
                    'name': field.name,
                    'reference_name': field.reference_name,
                    'type': field.type,
                    'usage': field.usage,
                    'read_only': field.read_only,
                    'is_identity': field.is_identity,
                    'is_picklist': field.is_picklist
                })
            
            logger.info(f"Retrieved {len(field_info)} field definitions")
            return field_info
        except Exception as e:
            logger.error(f"Failed to get field definitions: {str(e)}")
            raise

# if __name__ == "__main__":
#     from api.auth import get_connection
#     from config.settings import AZURE_DEVOPS_PROJECT
#     obj = AzureDevOpsCoreQueries(connection=get_connection(), project=AZURE_DEVOPS_PROJECT)

    # work_item_types = obj.get_work_item_types()
    # print("Work Item Types:")
    # for wit in work_item_types:
    #     print(f"- {wit['name']} ({wit['reference_name']})")

    # get_iteration_paths = obj.get_iteration_paths()
    # print(f"Iteration Paths: {get_iteration_paths}")

    # get_work_item = obj.get_work_item(3)
    # print(f"Work Item: {get_work_item}")

    # field_definitions = obj.get_field_definitions()
    # print("Field Definitions:")

