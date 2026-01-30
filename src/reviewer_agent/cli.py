import os
import sys
import json
from shared.llm import MockLLMClient, OpenAILLMClient
from reviewer_agent.service import ReviewerService

def main():
    print("Starting Reviewer Agent...")
    
    # 1. Read Event Path logic (Adapter logic)
    event_path = os.getenv("GITHUB_EVENT_PATH")
    
    # CLI Overrides can be nice too, but let's stick to GitHub Action structure
    # But we want to separate logic
    
    pr_number = None
    repo_name = None
    pr_body = None

    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, 'r') as f:
                event_data = json.load(f)
            # Assuming pull_request event
            if "pull_request" in event_data:
                pr_number = event_data["number"]
                repo_name = event_data["repository"]["full_name"]
                pr_body = event_data["pull_request"]["body"]
            else:
                 print("Not a pull_request event.")
                 # Fallback?
        except Exception as e:
            print(f"Error reading event file: {e}")
    else:
         # Fallback / Local Dev / Mock
         if os.path.exists("event.json"):
             print("Using local event.json mock.")
             try:
                with open("event.json", 'r') as f:
                    event_data = json.load(f)
                pr_number = event_data.get("number")
                repo_name = event_data.get("repository", {}).get("full_name")
                pr_body = event_data.get("pull_request", {}).get("body")
             except: 
                 pass
         
         if not pr_number:
              # Fallback defaults for dev
              pr_number = 1
              repo_name = "test/repo"
              pr_body = "Fixes #1"

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set.")
        sys.exit(1)

    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        llm_client = OpenAILLMClient(api_key=api_key)
    else:
        llm_client = MockLLMClient()

    service = ReviewerService(token, repo_name, llm_client)
    service.process_pr_review(pr_number, pr_body)

if __name__ == "__main__":
    main()
