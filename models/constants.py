"""
Constants for Azure DevOps work items.
This file is auto-generated by the generate_constants.py script.
Do not modify directly - your changes would be overwritten.
"""

class WorkItemType:
    """Constants for work item types."""
    BUG = "Microsoft.VSTS.WorkItemTypes.Bug"
    CODE_REVIEW_REQUEST = "Microsoft.VSTS.WorkItemTypes.CodeReviewRequest"
    CODE_REVIEW_RESPONSE = "Microsoft.VSTS.WorkItemTypes.CodeReviewResponse"
    EPIC = "Microsoft.VSTS.WorkItemTypes.Epic"
    FEATURE = "Microsoft.VSTS.WorkItemTypes.Feature"
    FEEDBACK_REQUEST = "Microsoft.VSTS.WorkItemTypes.FeedbackRequest"
    FEEDBACK_RESPONSE = "Microsoft.VSTS.WorkItemTypes.FeedbackResponse"
    SHARED_STEPS = "Microsoft.VSTS.WorkItemTypes.SharedStep"
    TASK = "Microsoft.VSTS.WorkItemTypes.Task"
    TEST_CASE = "Microsoft.VSTS.WorkItemTypes.TestCase"
    TEST_PLAN = "Microsoft.VSTS.WorkItemTypes.TestPlan"
    TEST_SUITE = "Microsoft.VSTS.WorkItemTypes.TestSuite"
    USER_STORY = "Microsoft.VSTS.WorkItemTypes.UserStory"
    ISSUE = "Microsoft.VSTS.WorkItemTypes.Issue"
    SHARED_PARAMETER = "Microsoft.VSTS.WorkItemTypes.SharedParameter"

class AreaPath:
    pass

class IterationPath:
    pass

class Field:
    """Constants for fields."""
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

class LinkType:
    """Constants for link types."""
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

