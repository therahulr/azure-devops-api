# Azure DevOps API Reference Guide

This document provides a comprehensive reference for the Azure DevOps REST API and Python SDK functions necessary for managing work items, test cases, and related operations.

## Table of Contents

- [Authentication & Setup](#authentication--setup)
- [Core Query APIs](#core-query-apis)
- [Work Item Management](#work-item-management)
- [Test Case Management](#test-case-management)
- [Attachments & Relations](#attachments--relations)
- [Querying with WIQL](#querying-with-wiql)

## Authentication & Setup

### Personal Access Token (PAT) Authentication

**API Type:** REST/SDK Authentication  
**Purpose:** Authenticate to Azure DevOps services

#### Required Information:
- **Organization URL:** `https://dev.azure.com/{organization}`
- **Personal Access Token (PAT):** Generated from Azure DevOps user settings
- **Project Name:** Your project identifier
- **API Version:** 7.1 (current recommended version)

#### REST Authentication Header:
```
Authorization: Basic <BASE64_ENCODED_PAT>
```
*Note: The string to encode is typically `:PAT` (a colon followed by the PAT)*

#### Python SDK Authentication:
```python
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

credentials = BasicAuthentication('', personal_access_token)
connection = Connection(base_url=organization_url, creds=credentials)
```

#### Required PAT Scopes:
- **vso.work_write** - For creating/updating work items/test cases
- **vso.test** - For test case operations
- **vso.work** - For reading work items

---

## Core Query APIs

### Get Work Item Types

**API Type:** REST/SDK  
**Purpose:** Retrieve all work item types in a project  
**Python Method:** `get_work_item_types()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitemtypes?api-version=7.1
```

#### Python SDK:
```python
work_item_types = wit_client.get_work_item_types(project)
```

#### Response:
Returns a list of work item types with names, reference names, descriptions, and icons.

---

### Get Area Paths

**API Type:** REST/SDK  
**Purpose:** Retrieve area path hierarchy  
**Python Method:** `get_area_paths()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/wit/classificationnodes/Areas?$depth=20&api-version=7.1
```

#### Python SDK:
```python
area_paths = wit_client.get_classification_nodes(project, depth=20, structure_type='Areas')
```

#### Response:
Returns a hierarchical structure of area paths with names, paths, and IDs.

---

### Get Iteration Paths

**API Type:** REST/SDK  
**Purpose:** Retrieve all sprints/iterations  
**Python Method:** `get_iteration_paths()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/wit/classificationnodes/Iterations?$depth=20&api-version=7.1
```

#### Python SDK:
```python
iteration_paths = wit_client.get_classification_nodes(project, depth=20, structure_type='Iterations')
```

#### Response:
Returns a hierarchical structure of iterations with names, paths, IDs, and date ranges.

---

### Get Work Item Details

**API Type:** REST/SDK  
**Purpose:** Retrieve a specific work item  
**Python Method:** `get_work_item()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?$expand=all&api-version=7.1
```

#### Python SDK:
```python
work_item = wit_client.get_work_item(id=work_item_id, expand="All")
```

#### Parameters:
- **id**: ID of the work item to retrieve
- **expand**: What to expand in the result (None, Relations, Fields, Links, All)

#### Response:
Returns detailed information about the work item including fields, relations, etc.

---

### Get Multiple Work Items

**API Type:** REST/SDK  
**Purpose:** Retrieve multiple work items in batch  
**Python Method:** `get_work_items()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/wit/workitems?ids=1,2,3&$expand=all&api-version=7.1
```

#### Python SDK:
```python
work_items = wit_client.get_work_items(ids=[1, 2, 3], expand="All")
```

#### Parameters:
- **ids**: List of work item IDs to retrieve (maximum 200 per request)
- **expand**: What to expand in the result (None, Relations, Fields, Links, All)

#### Response:
Returns a list of work items with detailed information.

---

### Get Field Definitions

**API Type:** REST/SDK  
**Purpose:** Retrieve available field definitions  
**Python Method:** `get_field_definitions()`

#### REST API:
```
GET https://dev.azure.com/{organization}/_apis/wit/fields?api-version=7.1
```

#### Python SDK:
```python
fields = wit_client.get_fields()
```

#### Response:
Returns a list of field definitions including names, reference names, types, etc.

---

## Work Item Management

### Create Work Item

**API Type:** REST/SDK  
**Purpose:** Create a new work item  
**Python Method:** `create_work_item()`

#### REST API:
```
POST https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/${type}?api-version=7.1
Content-Type: application/json-patch+json
```

#### Request Body (JSON Patch):
```json
[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "New Work Item"
  },
  {
    "op": "add",
    "path": "/fields/System.Description",
    "value": "Description of the work item"
  },
  {
    "op": "add",
    "path": "/fields/System.AssignedTo",
    "value": "user@example.com"
  }
]
```

#### Python SDK:
```python
document = [
    JsonPatchOperation(
        op="add",
        path="/fields/System.Title",
        value="New Work Item"
    ),
    JsonPatchOperation(
        op="add",
        path="/fields/System.Description",
        value="Description of the work item"
    )
]

work_item = wit_client.create_work_item(
    document=document,
    project=project,
    type="Task"
)
```

#### Parameters:
- **document**: List of JSON Patch operations defining field values
- **project**: Project name or ID
- **type**: Work item type (e.g., Task, Bug, User Story)

#### Response:
Returns the created work item details.

---

### Update Work Item

**API Type:** REST/SDK  
**Purpose:** Update an existing work item  
**Python Method:** `update_work_item()`

#### REST API:
```
PATCH https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?api-version=7.1
Content-Type: application/json-patch+json
```

#### Request Body (JSON Patch):
```json
[
  {
    "op": "add",
    "path": "/fields/System.State",
    "value": "Active"
  },
  {
    "op": "test",
    "path": "/rev",
    "value": 1
  }
]
```

#### Python SDK:
```python
document = [
    JsonPatchOperation(
        op="add",
        path="/fields/System.State",
        value="Active"
    ),
    JsonPatchOperation(
        op="test",
        path="/rev",
        value=1
    )
]

updated_work_item = wit_client.update_work_item(
    document=document,
    id=work_item_id
)
```

#### Parameters:
- **document**: List of JSON Patch operations defining changes
- **id**: ID of the work item to update

#### Response:
Returns the updated work item details.

---

### Create Child Work Item

**API Type:** REST/SDK  
**Purpose:** Create a child work item linked to a parent  
**Python Method:** `create_child_work_item()`

#### Python Implementation:
```python
# 1. Create the child work item first
child = create_work_item(...)

# 2. Create the parent-child relationship
relation_document = [
    JsonPatchOperation(
        op="add",
        path="/relations/-",
        value={
            "rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": f"{organization_url}/{project}/_apis/wit/workItems/{parent_id}"
        }
    )
]

updated_child = wit_client.update_work_item(
    document=relation_document,
    id=child.id
)
```

#### Parameters:
- **parent_id**: ID of the parent work item
- **work_item_type**: Type of work item to create
- **title**: Title of the child work item
- **description**: Description of the child work item (optional)
- **assigned_to**: User to assign the child work item to (optional)
- **additional_fields**: Dictionary of additional fields to set (optional)

#### Response:
Returns the created child work item with the parent relationship established.

---

## Test Case Management

### Create Test Case

**API Type:** REST/SDK  
**Purpose:** Create a new test case  
**Python Method:** `create_test_case()`

#### REST API:
```
POST https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/$Test%20Case?api-version=7.1
Content-Type: application/json-patch+json
```

#### Request Body (JSON Patch):
```json
[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "Sample Test Case"
  }
]
```

#### Python SDK:
```python
document = [
    JsonPatchOperation(
        op="add",
        path="/fields/System.Title",
        value="Sample Test Case"
    )
]

test_case = wit_client.create_work_item(
    document=document,
    project=project,
    type="Test Case"
)
```

#### Parameters:
- **title**: Title of the test case
- **description**: Description of the test case (optional)
- **area_path**: Area path for the test case (optional)
- **iteration_path**: Iteration path for the test case (optional)

#### Response:
Returns the created test case details.

---

### Add Test Steps

**API Type:** REST/SDK  
**Purpose:** Add steps to a test case  
**Python Method:** `add_test_steps()`

#### REST API:
```
PATCH https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{test_case_id}?api-version=7.1
Content-Type: application/json-patch+json
```

#### Request Body (JSON Patch):
```json
[
  {
    "op": "add",
    "path": "/fields/Microsoft.VSTS.TCM.Steps",
    "value": "<steps id=\"0\" last=\"2\"><step id=\"1\" type=\"ActionStep\"><parameterizedString isformatted=\"true\">Action 1</parameterizedString><description isformatted=\"true\">Expected Result 1</description></step><step id=\"2\" type=\"ActionStep\"><parameterizedString isformatted=\"true\">Action 2</parameterizedString><description isformatted=\"true\">Expected Result 2</description></step></steps>"
  }
]
```

#### Python Implementation:
```python
# Get current steps if they exist
test_case = wit_client.get_work_item(id=test_case_id)
current_steps_xml = test_case.fields.get('Microsoft.VSTS.TCM.Steps', '')

# Parse existing or create new XML
# ... XML manipulation logic ...

# Update the test case with new steps
document = [
    JsonPatchOperation(
        op="add",
        path="/fields/Microsoft.VSTS.TCM.Steps",
        value=steps_xml
    )
]

updated_test_case = wit_client.update_work_item(
    document=document,
    id=test_case_id
)
```

#### Parameters:
- **test_case_id**: ID of the test case
- **test_steps**: List of dictionaries with 'action' and 'expected' keys

#### Response:
Returns the updated test case with steps added.

---

### Update Test Steps

**API Type:** REST/SDK  
**Purpose:** Replace all test steps in a test case  
**Python Method:** `update_test_steps()`

#### Python Implementation:
```python
# Create new steps XML
# ... XML generation logic ...

# Update the test case with new steps
document = [
    JsonPatchOperation(
        op="add",
        path="/fields/Microsoft.VSTS.TCM.Steps",
        value=steps_xml
    )
]

updated_test_case = wit_client.update_work_item(
    document=document,
    id=test_case_id
)
```

#### Parameters:
- **test_case_id**: ID of the test case
- **test_steps**: List of dictionaries with 'action' and 'expected' keys

#### Response:
Returns the updated test case with replaced steps.

---

### Get Test Plans

**API Type:** REST/SDK  
**Purpose:** Get all test plans in a project  
**Python Method:** `get_test_plans()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/test/plans?api-version=7.1
```

#### Python SDK:
```python
plans = test_client.get_plans(project=project)
```

#### Response:
Returns a list of test plans.

---

### Get Test Suites

**API Type:** REST/SDK  
**Purpose:** Get test suites in a test plan  
**Python Method:** `get_test_suites()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/test/plans/{plan_id}/suites?api-version=7.1
```

#### Python SDK:
```python
suites = test_client.get_test_suites_for_plan(
    project=project,
    plan_id=plan_id
)
```

#### Parameters:
- **plan_id**: ID of the test plan

#### Response:
Returns a list of test suites in the specified plan.

---

### Get Test Cases in Suite

**API Type:** REST/SDK  
**Purpose:** Get test cases in a test suite  
**Python Method:** `get_test_cases_in_suite()`

#### REST API:
```
GET https://dev.azure.com/{organization}/{project}/_apis/test/plans/{plan_id}/suites/{suite_id}/testcases?api-version=7.1
```

#### Python SDK:
```python
test_cases = test_client.get_test_cases(
    project=project,
    plan_id=plan_id,
    suite_id=suite_id
)
```

#### Parameters:
- **plan_id**: ID of the test plan
- **suite_id**: ID of the test suite

#### Response:
Returns a list of test cases in the specified suite.

---

### Add Test Case to Suite

**API Type:** REST/SDK  
**Purpose:** Add a test case to a test suite  
**Python Method:** `add_test_case_to_suite()`

#### REST API:
```
POST https://dev.azure.com/{organization}/{project}/_apis/test/plans/{plan_id}/suites/{suite_id}/testcases/{test_case_id}?api-version=7.1
```

#### Python Implementation:
```python
url = f"{organization_url}/{project}/_apis/test/plans/{plan_id}/suites/{suite_id}/testcases/{test_case_id}?api-version=7.1"
auth_header = requests.auth.HTTPBasicAuth('', pat)
response = requests.post(url, auth=auth_header)
response.raise_for_status()
```

#### Parameters:
- **plan_id**: ID of the test plan
- **suite_id**: ID of the test suite
- **test_case_id**: ID of the test case

#### Response:
Returns the result of the operation.

---

## Attachments & Relations

### Upload Attachment

**API Type:** REST/SDK  
**Purpose:** Upload a file as an attachment  
**Python Method:** Uses direct REST API

#### REST API:
```
POST https://dev.azure.com/{organization}/{project}/_apis/wit/attachments?fileName={fileName}&api-version=7.1
Content-Type: application/octet-stream
```

#### Request Body:
Raw binary content of the file.

#### Python Implementation:
```python
# This usually requires direct REST calls
url = f"{organization_url}/{project}/_apis/wit/attachments?fileName={file_name}&api-version=7.1"
headers = {'Content-Type': 'application/octet-stream'}
auth = requests.auth.HTTPBasicAuth('', pat)

with open(file_path, 'rb') as f:
    file_content = f.read()
    
response = requests.post(url, headers=headers, auth=auth, data=file_content)
response.raise_for_status()
attachment_info = response.json()
```

#### Parameters:
- **fileName**: Name to use for the attachment in Azure DevOps
- **file_content**: Binary content of the file

#### Response:
Returns information about the uploaded attachment, including URL for linking.

---

### Link Attachment to Work Item

**API Type:** REST/SDK  
**Purpose:** Link an uploaded attachment to a work item  
**Python Method:** Uses work item update

#### REST API:
```
PATCH https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{id}?api-version=7.1
Content-Type: application/json-patch+json
```

#### Request Body (JSON Patch):
```json
[
  {
    "op": "add",
    "path": "/relations/-",
    "value": {
      "rel": "AttachedFile",
      "url": "attachment_url_from_upload_response",
      "attributes": {
        "comment": "Attachment description"
      }
    }
  }
]
```

#### Python Implementation:
```python
document = [
    JsonPatchOperation(
        op="add",
        path="/relations/-",
        value={
            "rel": "AttachedFile",
            "url": attachment_url,
            "attributes": {
                "comment": comment
            }
        }
    )
]

updated_work_item = wit_client.update_work_item(
    document=document,
    id=work_item_id
)
```

#### Parameters:
- **work_item_id**: ID of the work item
- **attachment_url**: URL of the uploaded attachment
- **comment**: Optional comment for the attachment

#### Response:
Returns the updated work item with the attachment linked.

---

## Querying with WIQL

### Execute WIQL Query

**API Type:** REST/SDK  
**Purpose:** Query work items using WIQL  
**Python Method:** `query_work_items()`

#### REST API:
```
POST https://dev.azure.com/{organization}/{project}/_apis/wit/wiql?api-version=7.1
Content-Type: application/json
```

#### Request Body:
```json
{
  "query": "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.WorkItemType] = 'Bug' AND [System.State] <> 'Closed' ORDER BY [System.ChangedDate] DESC"
}
```

#### Python SDK:
```python
wiql = Wiql(query=query_string)
query_result = wit_client.query_by_wiql(wiql)
work_item_references = query_result.work_items
```

#### Parameters:
- **query_string**: The WIQL query string

#### Response:
Returns a list of work item references (ID and URL) matching the query.

---

### Get Queried Work Items with Details

**API Type:** REST/SDK  
**Purpose:** Execute a WIQL query and retrieve full details  
**Python Method:** `get_queried_work_items()`

#### Python Implementation:
```python
# First get the work item references from the query
wiql = Wiql(query=query_string)
query_result = wit_client.query_by_wiql(wiql)
work_item_references = query_result.work_items

# Extract the IDs
work_item_ids = [int(reference.id) for reference in work_item_references]

# Get the full work item details
work_items = wit_client.get_work_items(ids=work_item_ids, expand="All")
```

#### Parameters:
- **query_string**: The WIQL query string
- **expand**: What to expand in the result (None, Relations, Fields, Links, All)

#### Response:
Returns a list of work item objects with full details.

---

## Common WIQL Example Queries

### 1. Recent Work Items Assigned to Current User

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.TeamProject] = @project
AND [System.AssignedTo] = @Me
ORDER BY [System.ChangedDate] DESC
```

### 2. Open Bugs in Current Iteration

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = @project
AND [System.WorkItemType] = 'Bug'
AND [System.State] <> 'Closed'
AND [System.IterationPath] = @CurrentIteration
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### 3. Test Cases Related to a Specific Work Item

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItemLinks
WHERE [Source].[System.Id] = 123
AND [Source].[System.TeamProject] = @project
AND [Target].[System.WorkItemType] = 'Test Case'
AND [System.Links.LinkType] = 'Microsoft.VSTS.Common.TestedBy-Forward'
MODE (MustContain)
```

### 4. Child Work Items Under a Parent

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItemLinks
WHERE [Source].[System.Id] = 123
AND [Source].[System.TeamProject] = @project
AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
MODE (MustContain)
```

---

## Best Practices

1. **Authentication:**
   - Store PATs securely (environment variables, secret management)
   - Use the principle of least privilege when defining scopes
   - Implement regular PAT rotation

2. **API Usage:**
   - Always specify the API version (api-version=7.1)
   - Handle rate limits with appropriate backoff strategies
   - Batch work item retrievals (maximum 200 per request)

3. **Data Consistency:**
   - Use optimistic concurrency control with the "test" operation on "/rev"
   - Validate inputs before sending to the API
   - Use validateOnly=true parameter during testing

4. **Error Handling:**
   - Implement comprehensive error handling with retry logic
   - Parse error responses for detailed information
   - Handle multi-step operations carefully (attachments, test steps)

5. **Test Steps:**
   - Use proper XML structure for test steps
   - Validate generated XML before submitting
   - Consider using XML libraries instead of string manipulation