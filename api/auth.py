"""
Authentication module for Azure DevOps API.
"""
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import sys
import logging

# Import from config package
sys.path.append("../")
from config.settings import AZURE_DEVOPS_ORG, AZURE_DEVOPS_PAT

logger = logging.getLogger(__name__)

def get_connection():
    """
    Create and return an authenticated connection to Azure DevOps.
    
    Returns:
        Connection: Authenticated Azure DevOps connection
    """
    if not AZURE_DEVOPS_ORG or not AZURE_DEVOPS_PAT:
        logger.error("Azure DevOps organization URL or Personal Access Token not configured.")
        raise ValueError("Missing required authentication credentials")
    
    try:
        # Create a connection to Azure DevOps
        credentials = BasicAuthentication('', AZURE_DEVOPS_PAT)
        connection = Connection(base_url=AZURE_DEVOPS_ORG, creds=credentials)
        
        # Test the connection
        core_client = connection.clients.get_core_client()
        projects = core_client.get_projects()
        logger.info(f"Successfully connected to Azure DevOps. Found {len(list(projects))} projects.")
        
        return connection
    except Exception as e:
        logger.error(f"Failed to establish connection to Azure DevOps: {str(e)}")
        raise