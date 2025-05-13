import os
import json
import pandas as pd
import argparse
import logging
import time
import tiktoken
import asyncio
from pathlib import Path
from openai import OpenAI, AsyncOpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import jsonschema

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
success_logger = logging.getLogger('success')
failure_logger = logging.getLogger('failure')

# Set up file handlers for success and failure logs
success_handler = logging.FileHandler('success.log')
failure_handler = logging.FileHandler('failure.log')
success_logger.addHandler(success_handler)
failure_logger.addHandler(failure_handler)
success_logger.setLevel(logging.INFO)
failure_logger.setLevel(logging.INFO)

# Define the JSON schema for validation
TEST_CASE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["type", "title", "description", "automation_status", "test_steps", "additional_fields"],
        "properties": {
            "type": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "automation_status": {"type": "string"},
            "test_steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["action", "expected"],
                    "properties": {
                        "action": {"type": "string"},
                        "expected": {"type": "string"}
                    }
                }
            },
            "additional_fields": {
                "type": "object",
                "required": ["Microsoft.VSTS.Common.Priority", "System.Tags"],
                "properties": {
                    "Microsoft.VSTS.Common.Priority": {"type": "integer"},
                    "System.Tags": {"type": "string"},
                    "System.AreaPath": {"type": "string"},
                    "System.IterationPath": {"type": "string"},
                    "System.AssignedTo": {"type": "string"}
                }
            }
        }
    }
}

class RateLimiter:
    """Rate limiter for API calls"""
    def __init__(self, requests_per_minute=60):
        self.request_interval = 60.0 / requests_per_minute
        self.last_request_time = 0
        
    def wait(self):
        """Wait if needed to respect rate limits"""
        elapsed_time = time.time() - self.last_request_time
        wait_time = max(0, self.request_interval - elapsed_time)
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_request_time = time.time()

class TestCaseProcessor:
    def __init__(self, api_key=None, model="gpt-4.1", ado_area_path="Inficore", ado_iteration_path="Inficore\Sprint 1", ado_assigned_to="rahulraj.cs26@gmail.com"):
        # Initialize OpenAI client
        if api_key is None:
            # api_key = os.getenv("OPENAI_API_KEY")
            api_key = "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"
            if api_key is None:
                raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.rate_limiter = RateLimiter()
        self.encoding = tiktoken.encoding_for_model(model)
        
        # Azure DevOps specific fields
        self.ado_area_path = ado_area_path
        self.ado_iteration_path = ado_iteration_path
        self.ado_assigned_to = ado_assigned_to
        
        # Track processed folders
        self.processed_folders = set()
        
    def count_tokens(self, text):
        """Count tokens in a string using tiktoken"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logging.warning(f"Error counting tokens: {str(e)}. Using fallback method.")
            # Fallback method: rough estimate (~4 chars per token)
            return len(text) // 4
    
    def extract_test_case_details(self, excel_file):
        """Extract test case details from Excel file"""
        try:
            df = pd.read_excel(excel_file)
            
            # Based on the example, find key columns
            key_col = None
            summary_col = None
            description_col = None
            priority_col = None
            
            # Check for expected column names based on the example
            for col in df.columns:
                col_str = str(col).lower()
                if col_str == 'key':
                    key_col = col
                elif col_str == 'summary':
                    summary_col = col
                elif col_str == 'description':
                    description_col = col
                elif col_str == 'priority':
                    priority_col = col
            
            # Ensure we have the minimum required columns
            if not summary_col or not description_col:
                raise ValueError(f"Required columns 'summary' and 'description' not found in {excel_file}")
            
            # Extract the data
            key = str(df[key_col].iloc[0]) if key_col and not pd.isna(df[key_col].iloc[0]) else ""
            summary = str(df[summary_col].iloc[0]) if not pd.isna(df[summary_col].iloc[0]) else ""
            description = str(df[description_col].iloc[0]) if not pd.isna(df[description_col].iloc[0]) else ""
            
            # Parse priority
            priority = "Medium"
            if priority_col and not pd.isna(df[priority_col].iloc[0]):
                priority = str(df[priority_col].iloc[0])
            
            # Convert priority to numeric value
            priority_map = {
                'highest': 1,
                'high': 1,
                'medium': 2,
                'low': 3,
                'lowest': 4
            }
            
            priority_value = priority_map.get(priority.lower(), 2)
            
            return {
                "key": key,
                "summary": summary,
                "description": description,
                "priority": priority,
                "priority_value": priority_value
            }
            
        except Exception as e:
            raise Exception(f"Error extracting test case details: {str(e)}")
    
    def extract_steps(self, csv_file):
        """Extract test steps from CSV file"""
        try:
            df = pd.read_csv(csv_file)
            
            # Figure out column names from the example format
            step_col = None
            test_data_col = None
            expected_col = None
            
            for col in df.columns:
                col_str = str(col).lower()
                if col_str == '#' or col_str == 'step':
                    step_col = col
                elif 'test data' in col_str:
                    test_data_col = col
                elif 'expected' in col_str or 'result' in col_str:
                    expected_col = col
            
            # If we can't find exact column names, try to infer
            if not step_col and len(df.columns) >= 1:
                step_col = df.columns[0]  # Assume first column is step number
            
            if not expected_col and len(df.columns) >= 3:
                expected_col = df.columns[2]  # Assume third column is expected result
            
            if not test_data_col and len(df.columns) >= 2:
                test_data_col = df.columns[1]  # Assume second column is test data
            
            # Ensure we have the minimum required columns
            if not step_col or not expected_col:
                raise ValueError(f"Required step or expected result columns not found in {csv_file}")
            
            steps = []
            for _, row in df.iterrows():
                # Get step
                step_val = row[step_col] if not pd.isna(row[step_col]) else ""
                
                # Handle if step is just a number
                if isinstance(step_val, (int, float)) or (isinstance(step_val, str) and step_val.isdigit()):
                    # If step column is just numbers, use the second column as the actual step text
                    if len(df.columns) > 1:
                        action_col = df.columns[1] if df.columns[1] != expected_col else df.columns[0]
                        action = str(row[action_col]) if not pd.isna(row[action_col]) else ""
                    else:
                        action = f"Step {step_val}"
                else:
                    action = str(step_val)
                
                # Include test data if available
                if test_data_col and not pd.isna(row[test_data_col]) and str(row[test_data_col]):
                    test_data = str(row[test_data_col])
                    if not action.endswith(test_data):
                        action += f" with data: {test_data}"
                
                # Get expected result
                expected = str(row[expected_col]) if not pd.isna(row[expected_col]) else ""
                
                if action or expected:
                    steps.append({"action": action, "expected": expected})
            
            return steps
            
        except Exception as e:
            raise Exception(f"Error extracting steps: {str(e)}")
    
    def prepare_test_case_prompt(self, test_case_data, steps_data, folder_name):
        """Prepare the prompt for a single test case"""
        
        # Determine if this is for UNO or OSC based on the test case content
        application_type = "UNO (desktop application)"
        if "OSC" in test_case_data.get("summary", "") or "Online Sales Center" in test_case_data.get("description", ""):
            application_type = "OSC (Online Sales Center, web application)"
        
        # Format steps for the prompt
        steps_text = ""
        for i, step in enumerate(steps_data, 1):
            steps_text += f"Step {i}: {step['action']}\nExpected: {step['expected']}\n\n"
        
        # Create the prompt for this test case
        prompt = f"""
        I have a test case for {application_type} that needs to be reformatted according to a specific template schema.
        
        Test Case Key: {test_case_data.get('key', '')}
        
        Test Case Summary: {test_case_data.get('summary', '')}
        
        Test Case Description: {test_case_data.get('description', '')}
        
        Test Case Steps:
        {steps_text}
        
        Please rewrite this test case to be grammatically correct, well-formatted, and clearly organized. 
        You must strictly adhere to the following output JSON template schema:
        
        ```json
        [
          {{
            "type": "Test Case",
            "title": "Improved and professional test case title",
            "description": "<div><p><strong>Test Objective:</strong> Clear statement of what this test is verifying</p><p><strong>Test Environment:</strong> The environment where this test should be performed</p><p><strong>Pre-requisites:</strong></p><ul><li>Required setup step 1</li><li>Required setup step 2</li></ul><p><strong>Expected Behavior:</strong> Any relevant expectations</p></div>",
            "automation_status": "Not Automated",
            "test_steps": [
              {{
                "action": "Clear, well-written action step",
                "expected": "Clear expected result"
              }}
            ],
            "additional_fields": {{
              "Microsoft.VSTS.Common.Priority": {test_case_data.get('priority_value', 2)},
              "System.Tags": "Relevant; Tags; Based; On; Content",
              "System.AreaPath": "{self.ado_area_path if self.ado_area_path else ''}",
              "System.IterationPath": "{self.ado_iteration_path if self.ado_iteration_path else ''}",
              "System.AssignedTo": "{self.ado_assigned_to if self.ado_assigned_to else ''}"
            }}
          }}
        ]
        ```
        
        Important guidelines:
        1. The "description" must use proper HTML format with div, p, strong, and ul/li tags exactly as shown
        2. Make the title professional and concise
        3. Identify test objective clearly from the context
        4. Include meaningful tags related to the test case
        5. Maintain all steps in the proper order but improve their clarity
        6. Ensure all steps have both an action and an expected result
        7. The JSON must be perfectly valid, with no syntax errors
        
        Only return the valid JSON with no other text or explanation.
        """
        
        return {
            "folder_name": folder_name,
            "test_case_data": test_case_data,
            "prompt": prompt,
            "token_count": self.count_tokens(prompt)
        }

    def validate_json(self, json_data):
        """Validate the JSON output against our schema"""
        try:
            jsonschema.validate(instance=json_data, schema=TEST_CASE_SCHEMA)
            return True
        except jsonschema.exceptions.ValidationError as e:
            raise Exception(f"JSON validation failed: {str(e)}")
    
    async def process_batch_async(self, batch):
        """Process a batch of test cases asynchronously"""
        try:
            # Create the system message
            system_message = "You are a QA specialist who converts test cases into a standardized JSON format. Your output must be valid JSON that strictly follows the required schema with no additional text."
            
            # Create the message list
            messages = []
            for item in batch:
                messages.append({
                    "role": "system",
                    "content": system_message
                })
                messages.append({
                    "role": "user",
                    "content": item["prompt"]
                })
            
            # Process each test case in the batch
            tasks = []
            for i, item in enumerate(batch):
                self.rate_limiter.wait()  # Respect rate limits
                
                # Create the API call task
                task = asyncio.create_task(self._call_openai_api_async(
                    messages=[messages[i*2], messages[i*2+1]],
                    folder_name=item["folder_name"]
                ))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = 0
            failed = 0
            
            # Process results
            for i, result in enumerate(results):
                folder_name = batch[i]["folder_name"]
                
                if isinstance(result, Exception):
                    failure_logger.error(f"Failed to process {folder_name}: {str(result)}")
                    failed += 1
                else:
                    # Write the JSON output
                    output_file = f"{folder_name.lower()}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2)
                    
                    success_logger.info(f"Successfully processed {folder_name}")
                    self.processed_folders.add(folder_name)
                    successful += 1
            
            return successful, failed
            
        except Exception as e:
            logging.error(f"Error processing batch: {str(e)}")
            return 0, len(batch)
    
    async def _call_openai_api_async(self, messages, folder_name):
        """Call the OpenAI API asynchronously"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2500
                )
                
                # Extract and parse the response
                json_response = response.choices[0].message.content.strip()
                
                # Handle case where response might have markdown code block
                if json_response.startswith("```json"):
                    json_response = json_response[7:]  # Remove ```json
                if json_response.endswith("```"):
                    json_response = json_response[:-3]  # Remove ```
                
                json_response = json_response.strip()
                
                # Parse the JSON
                parsed_json = json.loads(json_response)
                
                # Validate the JSON
                self.validate_json(parsed_json)
                
                return parsed_json
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    logging.warning(f"JSON parsing error for {folder_name} on attempt {attempt+1}: {str(e)}. Retrying...")
                    # Exponential backoff
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"Failed to parse OpenAI response as JSON after {max_retries} attempts: {str(e)}")
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"API error for {folder_name} on attempt {attempt+1}: {str(e)}. Retrying...")
                    # Exponential backoff
                    wait_time = (2 ** attempt) + (0.1 * attempt)
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"Error calling OpenAI API after {max_retries} attempts: {str(e)}")
    
    def process_folder(self, folder_path):
        """Process a single folder containing test case files"""
        folder_name = os.path.basename(folder_path)
        logging.info(f"Processing folder: {folder_name}")
        
        # Find Excel and CSV files
        excel_files = list(Path(folder_path).glob("*.xlsx")) + list(Path(folder_path).glob("*.xls"))
        csv_files = list(Path(folder_path).glob("*.csv"))
        
        if not excel_files:
            failure_logger.error(f"No Excel file found in {folder_name}")
            return None
        
        if not csv_files:
            failure_logger.error(f"No CSV file found in {folder_name}")
            return None
        
        excel_file = excel_files[0]
        csv_file = csv_files[0]
        
        try:
            # Extract test case details from Excel
            test_case_data = self.extract_test_case_details(excel_file)
            
            # Extract steps from CSV
            steps_data = self.extract_steps(csv_file)
            
            # Prepare the prompt for this test case
            prompt_data = self.prepare_test_case_prompt(test_case_data, steps_data, folder_name)
            
            return prompt_data
            
        except Exception as e:
            failure_logger.error(f"Failed to prepare {folder_name}: {str(e)}")
            return None
    
    async def process_multiple_folders(self, folders, max_batch_size=5, max_tokens_per_batch=30000):
        """Process multiple folders by batching test cases"""
        batches = []
        current_batch = []
        current_batch_tokens = 0
        
        # Prepare all prompts
        prompts = []
        for folder in tqdm(folders, desc="Preparing test cases"):
            if os.path.basename(folder) in self.processed_folders:
                logging.info(f"Skipping already processed folder: {os.path.basename(folder)}")
                continue
                
            prompt_data = self.process_folder(folder)
            if prompt_data:
                prompts.append(prompt_data)
        
        # Sort prompts by token count to optimize batching
        prompts.sort(key=lambda x: x["token_count"])
        
        # Create batches based on token count
        for prompt in prompts:
            # If adding this prompt exceeds our token budget, start a new batch
            if len(current_batch) >= max_batch_size or current_batch_tokens + prompt["token_count"] > max_tokens_per_batch:
                if current_batch:  # Only add non-empty batches
                    batches.append(current_batch)
                current_batch = [prompt]
                current_batch_tokens = prompt["token_count"]
            else:
                current_batch.append(prompt)
                current_batch_tokens += prompt["token_count"]
        
        # Add the last batch if not empty
        if current_batch:
            batches.append(current_batch)
        
        logging.info(f"Created {len(batches)} batches from {len(prompts)} test cases")
        
        # Process all batches
        total_successful = 0
        total_failed = 0
        
        for i, batch in enumerate(batches):
            logging.info(f"Processing batch {i+1}/{len(batches)} with {len(batch)} test cases")
            
            successful, failed = await self.process_batch_async(batch)
            total_successful += successful
            total_failed += failed
            
            # Add delay between batches to avoid rate limits
            if i < len(batches) - 1:
                logging.info(f"Waiting between batches to avoid rate limits...")
                await asyncio.sleep(2)
        
        return total_successful, total_failed

def parse_args():
    parser = argparse.ArgumentParser(description='Process test case files with OpenAI')
    parser.add_argument('folder_path', help='Path to the main folder containing test case subfolders')
    parser.add_argument('--api-key', help='OpenAI API key (optional if set as environment variable)')
    parser.add_argument('--model', default='gpt-4o', help='OpenAI model to use (default: gpt-4o)')
    parser.add_argument('--folder', help='Process a specific folder by name')
    parser.add_argument('--all', action='store_true', help='Process all folders')
    parser.add_argument('--list', action='store_true', help='List all available folders')
    parser.add_argument('--batch-size', type=int, default=5, help='Maximum number of test cases to process in one batch')
    parser.add_argument('--area-path', help='Azure DevOps Area Path')
    parser.add_argument('--iteration-path', help='Azure DevOps Iteration Path')
    parser.add_argument('--assigned-to', help='Azure DevOps Assigned To')
    return parser.parse_args()

async def main_async():
    args = parse_args()
    
    main_folder = Path(args.folder_path)
    
    if not main_folder.exists() or not main_folder.is_dir():
        logging.error(f"The specified folder {args.folder_path} does not exist or is not a directory")
        return
    
    # Get all subfolders
    subfolders = [f for f in main_folder.iterdir() if f.is_dir()]
    
    if args.list:
        print(f"Found {len(subfolders)} folders:")
        for i, folder in enumerate(subfolders, 1):
            print(f"{i}. {folder.name}")
        return
    
    processor = TestCaseProcessor(
        api_key=args.api_key,
        model=args.model,
        ado_area_path=args.area_path,
        ado_iteration_path=args.iteration_path,
        ado_assigned_to=args.assigned_to
    )
    
    if args.folder:
        # Process specific folder
        target_folder = main_folder / args.folder
        if target_folder.exists() and target_folder.is_dir():
            prompt_data = processor.process_folder(target_folder)
            if prompt_data:
                successful, failed = await processor.process_multiple_folders([target_folder])
                print(f"Processing complete. Successful: {successful}, Failed: {failed}")
        else:
            logging.error(f"Folder {args.folder} not found in {main_folder}")
            return
    elif args.all:
        # Process all folders
        successful, failed = await processor.process_multiple_folders(
            subfolders, 
            max_batch_size=args.batch_size
        )
        
        print(f"\nProcessing complete. Successful: {successful}, Failed: {failed}")
        print(f"See success.log and failure.log for details.")
    else:
        # Interactive mode
        while True:
            print(f"\nFound {len(subfolders)} folders:")
            for i, folder in enumerate(subfolders, 1):
                print(f"{i}. {folder.name}")
            
            print("\nOptions:")
            print("A. Process all folders")
            print("B. Process a batch of folders")
            print("Q. Quit")
            
            choice = input("\nEnter folder number, 'A' for all, 'B' for batch, or 'Q' to quit: ")
            
            if choice.upper() == 'Q':
                break
            elif choice.upper() == 'A':
                successful, failed = await processor.process_multiple_folders(
                    subfolders, 
                    max_batch_size=args.batch_size
                )
                
                print(f"\nProcessing complete. Successful: {successful}, Failed: {failed}")
                print(f"See success.log and failure.log for details.")
                break
            elif choice.upper() == 'B':
                batch_size = int(input("How many folders to process in this batch? "))
                folders_to_process = []
                
                for _ in range(min(batch_size, len(subfolders))):
                    folder_idx = int(input(f"Enter folder number (1-{len(subfolders)}): ")) - 1
                    if 0 <= folder_idx < len(subfolders):
                        folders_to_process.append(subfolders[folder_idx])
                    else:
                        print("Invalid folder number.")
                
                if folders_to_process:
                    successful, failed = await processor.process_multiple_folders(
                        folders_to_process, 
                        max_batch_size=args.batch_size
                    )
                    
                    print(f"\nProcessing complete. Successful: {successful}, Failed: {failed}")
                    print(f"See success.log and failure.log for details.")
            else:
                try:
                    folder_idx = int(choice) - 1
                    if 0 <= folder_idx < len(subfolders):
                        prompt_data = processor.process_folder(subfolders[folder_idx])
                        if prompt_data:
                            successful, failed = await processor.process_multiple_folders([subfolders[folder_idx]])
                            print(f"Processing complete. Successful: {successful}, Failed: {failed}")
                    else:
                        print("Invalid folder number.")
                except ValueError:
                    print("Invalid input.")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()