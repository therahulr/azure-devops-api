import os
import json
import pandas as pd
import argparse
import logging
import jsonschema
from pathlib import Path
from openai import OpenAI
from tqdm import tqdm
import time

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
                    "System.Tags": {"type": "string"}
                }
            }
        }
    }
}

class TestCaseProcessor:
    def __init__(self, api_key=None):
        # Initialize OpenAI client
        if api_key is None:
            # api_key = os.getenv("OPENAI_API_KEY")
            api_key = "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"
            if api_key is None:
                raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=api_key)
        
    def process_folder(self, folder_path):
        """Process a single folder containing test case files"""
        folder_name = os.path.basename(folder_path)
        logging.info(f"Processing folder: {folder_name}")
        
        # Find Excel and CSV files
        excel_files = list(Path(folder_path).glob("*.xlsx")) + list(Path(folder_path).glob("*.xls"))
        csv_files = list(Path(folder_path).glob("*.csv"))
        
        if not excel_files:
            failure_logger.error(f"No Excel file found in {folder_name}")
            return False
        
        if not csv_files:
            failure_logger.error(f"No CSV file found in {folder_name}")
            return False
        
        excel_file = excel_files[0]
        csv_file = csv_files[0]
        
        try:
            # Extract test case details from Excel
            test_case_data = self.extract_test_case_details(excel_file)
            
            # Extract steps from CSV
            steps_data = self.extract_steps(csv_file)
            
            # Process with OpenAI
            formatted_test_case = self.format_with_openai(test_case_data, steps_data, folder_name)
            
            # Validate JSON
            self.validate_json(formatted_test_case)
            
            # Save as JSON
            output_file = os.path.join(os.path.dirname(folder_path), f"{folder_name.lower()}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_test_case, f, indent=2)
            
            success_logger.info(f"Successfully processed {folder_name}")
            return True
            
        except Exception as e:
            failure_logger.error(f"Failed to process {folder_name}: {str(e)}")
            return False
    
    def extract_test_case_details(self, excel_file):
        """Extract test case details from Excel file"""
        try:
            # For CSV-like or Excel files with specific structure
            df = pd.read_excel(excel_file)
            
            # Based on the example, the Excel might have specific column names
            # Extract by column names, handling both potential formats
            test_case_data = {}
            
            # Check if data is in columns format or possibly in rows
            if 'key' in df.columns and 'summary' in df.columns and 'description' in df.columns:
                # Format is columns with rows of data
                test_case_data = {
                    "key": df['key'].iloc[0] if not pd.isna(df['key'].iloc[0]) else "",
                    "summary": df['summary'].iloc[0] if not pd.isna(df['summary'].iloc[0]) else "",
                    "description": df['description'].iloc[0] if not pd.isna(df['description'].iloc[0]) else "",
                    "priority": df['priority'].iloc[0] if 'priority' in df.columns and not pd.isna(df['priority'].iloc[0]) else "Medium"
                }
            else:
                # Format might be rows with columns of data (transpose-like)
                # Look for specific keys in first column
                key_idx = df.index[df.iloc[:, 0] == 'key'].tolist()
                summary_idx = df.index[df.iloc[:, 0] == 'summary'].tolist()
                description_idx = df.index[df.iloc[:, 0] == 'description'].tolist()
                priority_idx = df.index[df.iloc[:, 0] == 'priority'].tolist()
                
                test_case_data = {
                    "key": df.iloc[key_idx[0], 1] if key_idx else "",
                    "summary": df.iloc[summary_idx[0], 1] if summary_idx else "",
                    "description": df.iloc[description_idx[0], 1] if description_idx else "",
                    "priority": df.iloc[priority_idx[0], 1] if priority_idx else "Medium"
                }
            
            # If the format is different from both approaches, try to find relevant columns by string matching
            if not test_case_data.get("summary") and not test_case_data.get("description"):
                # Try to find columns that might contain these values
                summary_col = None
                description_col = None
                priority_col = None
                
                for col in df.columns:
                    if 'summary' in str(col).lower() or 'title' in str(col).lower():
                        summary_col = col
                    elif 'description' in str(col).lower() or 'desc' in str(col).lower():
                        description_col = col
                    elif 'priority' in str(col).lower() or 'prio' in str(col).lower():
                        priority_col = col
                
                if summary_col:
                    test_case_data["summary"] = df[summary_col].iloc[0] if not pd.isna(df[summary_col].iloc[0]) else ""
                if description_col:
                    test_case_data["description"] = df[description_col].iloc[0] if not pd.isna(df[description_col].iloc[0]) else ""
                if priority_col:
                    test_case_data["priority"] = df[priority_col].iloc[0] if not pd.isna(df[priority_col].iloc[0]) else "Medium"
            
            # If still no data, try one more approach - transposed data scanning
            if not test_case_data.get("summary") and not test_case_data.get("description"):
                for i, row in df.iterrows():
                    for j, value in enumerate(row):
                        if str(value).lower() == 'summary':
                            test_case_data["summary"] = df.iloc[i, j+1] if j+1 < len(row) and not pd.isna(df.iloc[i, j+1]) else ""
                        elif str(value).lower() == 'description':
                            test_case_data["description"] = df.iloc[i, j+1] if j+1 < len(row) and not pd.isna(df.iloc[i, j+1]) else ""
                        elif str(value).lower() == 'priority':
                            test_case_data["priority"] = df.iloc[i, j+1] if j+1 < len(row) and not pd.isna(df.iloc[i, j+1]) else "Medium"
            
            # If still missing data, try a more direct approach and just get what we can
            if not test_case_data.get("key"):
                # Look for values that match Jira key pattern (e.g., UNOD-12)
                for col in df.columns:
                    for val in df[col]:
                        if isinstance(val, str) and '-' in val and any(char.isdigit() for char in val):
                            test_case_data["key"] = val
                            break
                    if test_case_data.get("key"):
                        break
            
            # Priority mapping
            priority_map = {
                'highest': 1,
                'high': 1,
                'medium': 2,
                'low': 3,
                'lowest': 4
            }
            
            if isinstance(test_case_data.get("priority"), str):
                priority_str = test_case_data.get("priority", "Medium").lower()
                test_case_data["priority_value"] = priority_map.get(priority_str, 2)
            else:
                test_case_data["priority_value"] = 2  # Default medium priority
            
            # Check if we have minimum required data
            if not test_case_data.get("summary") or not test_case_data.get("description"):
                logging.warning(f"Missing key data in {excel_file}. Using available data.")
            
            return test_case_data
            
        except Exception as e:
            raise Exception(f"Error extracting test case details: {str(e)}")
    
    def extract_steps(self, csv_file):
        """Extract test steps from CSV file"""
        try:
            df = pd.read_csv(csv_file)
            
            # Based on the example, find the relevant columns
            step_col = None
            test_data_col = None
            expected_col = None
            
            # Check for specific column names from the example
            for col in df.columns:
                col_str = str(col).lower()
                if col_str == '#' or col_str == 'step' or 'step' in col_str:
                    step_col = col
                elif 'test data' in col_str or 'testdata' in col_str:
                    test_data_col = col
                elif 'expected' in col_str or 'result' in col_str:
                    expected_col = col
            
            # If we couldn't find the columns, make an educated guess
            if not step_col:
                # Look for a column with numeric values (likely step numbers)
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        step_col = col
                        break
                
                if not step_col and len(df.columns) > 0:
                    step_col = df.columns[0]  # Default to first column
            
            if not expected_col and len(df.columns) > 1:
                expected_col = df.columns[-1]  # Default to last column for expected results
            
            # If test data column wasn't found but we have at least 3 columns, assume middle column
            if not test_data_col and len(df.columns) >= 3:
                test_data_col = df.columns[len(df.columns) // 2]
            
            if not step_col or not expected_col:
                raise ValueError(f"Could not identify steps or expected result columns in {csv_file}")
            
            steps = []
            for _, row in df.iterrows():
                step_text = str(row[step_col]) if not pd.isna(row[step_col]) else ""
                
                # Check if this is really a step number and not the step description
                if step_text.isdigit() and len(df.columns) >= 2:
                    # If step_col is just a number, the actual step description might be in the next column
                    step_idx = list(df.columns).index(step_col)
                    if step_idx + 1 < len(df.columns) and step_idx + 1 != list(df.columns).index(expected_col):
                        step_col_desc = df.columns[step_idx + 1]
                        step_text = str(row[step_col_desc]) if not pd.isna(row[step_col_desc]) else ""
                
                # Include test data if available
                test_data = ""
                if test_data_col and not pd.isna(row[test_data_col]):
                    test_data = str(row[test_data_col])
                    if test_data and not step_text.endswith(test_data):
                        step_text += f" with data: {test_data}"
                
                expected = str(row[expected_col]) if not pd.isna(row[expected_col]) else ""
                
                if step_text or expected:
                    steps.append({"action": step_text, "expected": expected})
            
            return steps
            
        except Exception as e:
            raise Exception(f"Error extracting steps: {str(e)}")
    
    def format_with_openai(self, test_case_data, steps_data, folder_name):
        """Use OpenAI to format and clean the test case data"""
        try:
            # Determine if this is for UNO or OSC based on the test case content
            application_type = "UNO (desktop application)"
            if "OSC" in test_case_data.get("summary", "") or "Online Sales Center" in test_case_data.get("description", ""):
                application_type = "OSC (Online Sales Center, web application)"
            
            # Create detailed test steps string for the prompt
            steps_text = ""
            for i, step in enumerate(steps_data, 1):
                steps_text += f"Step {i}: {step['action']}\nExpected: {step['expected']}\n\n"
            
            # Prepare the prompt
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
                  }},
                  // Additional steps as needed
                ],
                "additional_fields": {{
                  "Microsoft.VSTS.Common.Priority": {test_case_data.get('priority_value', 2)},
                  "System.Tags": "Choose; between; UNO; and; OSC; based; on; the; test case"
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
            
            # Call the OpenAI API with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4.1",  # Using the latest model
                        messages=[
                            {"role": "system", "content": "You are a QA specialist who converts test cases into a standardized JSON format considering sentence, gramatical issues, meaning, context etc. Your output must be valid JSON that strictly follows the required schema with no additional text."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,  # Lower temperature for more consistent output
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
                    
                    # Basic validation
                    if not isinstance(parsed_json, list) or not parsed_json:
                        raise ValueError("Response is not a valid JSON array or is empty")
                    
                    return parsed_json
                    
                except json.JSONDecodeError as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"JSON parsing error on attempt {attempt+1}: {str(e)}. Retrying...")
                        time.sleep(2)  # Wait before retrying
                    else:
                        raise Exception(f"Failed to parse OpenAI response as JSON after {max_retries} attempts: {str(e)}")
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"API error on attempt {attempt+1}: {str(e)}. Retrying...")
                        time.sleep(2)  # Wait before retrying
                    else:
                        raise Exception(f"Error calling OpenAI API after {max_retries} attempts: {str(e)}")
            
        except Exception as e:
            raise Exception(f"Error formatting with OpenAI: {str(e)}")
    
    def validate_json(self, json_data):
        """Validate the JSON output against our schema"""
        try:
            jsonschema.validate(instance=json_data, schema=TEST_CASE_SCHEMA)
            return True
        except jsonschema.exceptions.ValidationError as e:
            raise Exception(f"JSON validation failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Process test case files with OpenAI')
    parser.add_argument('folder_path', help='Path to the main folder containing test case subfolders')
    parser.add_argument('--api-key', help='OpenAI API key (optional if set as environment variable)')
    parser.add_argument('--folder', help='Process a specific folder by name')
    parser.add_argument('--all', action='store_true', help='Process all folders')
    parser.add_argument('--list', action='store_true', help='List all available folders')
    args = parser.parse_args()
    
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
    
    processor = TestCaseProcessor(api_key=args.api_key)
    
    if args.folder:
        # Process specific folder
        target_folder = main_folder / args.folder
        if target_folder.exists() and target_folder.is_dir():
            processor.process_folder(target_folder)
        else:
            logging.error(f"Folder {args.folder} not found in {main_folder}")
            return
    elif args.all:
        # Process all folders
        successful = 0
        failed = 0
        
        for folder in tqdm(subfolders, desc="Processing folders"):
            result = processor.process_folder(folder)
            if result:
                successful += 1
            else:
                failed += 1
            
            # Add a small delay to avoid rate limits
            time.sleep(1)
        
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
            print("Q. Quit")
            
            choice = input("\nEnter folder number, 'A' for all, or 'Q' to quit: ")
            
            if choice.upper() == 'Q':
                break
            elif choice.upper() == 'A':
                successful = 0
                failed = 0
                
                for folder in tqdm(subfolders, desc="Processing folders"):
                    result = processor.process_folder(folder)
                    if result:
                        successful += 1
                    else:
                        failed += 1
                    
                    # Add a small delay to avoid rate limits
                    time.sleep(1)
                
                print(f"\nProcessing complete. Successful: {successful}, Failed: {failed}")
                print(f"See success.log and failure.log for details.")
                break
            else:
                try:
                    folder_idx = int(choice) - 1
                    if 0 <= folder_idx < len(subfolders):
                        processor.process_folder(subfolders[folder_idx])
                    else:
                        print("Invalid folder number.")
                except ValueError:
                    print("Invalid input.")

if __name__ == "__main__":
    main()