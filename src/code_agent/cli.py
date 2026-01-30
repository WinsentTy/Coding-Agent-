import argparse
import os
import sys
from shared.llm import MockLLMClient, OpenAILLMClient
from code_agent.service import CodeAgentService

def main():
    parser = argparse.ArgumentParser(description="Code Agent CLI")
    parser.add_argument("--issue-id", type=int, help="GitHub Issue ID (for new fix)")
    parser.add_argument("--pr-number", type=int, help="GitHub PR Number (for feedback loop)")
    parser.add_argument("--repo", type=str, required=True, help="Repository name (owner/repo)")
    parser.add_argument("--token", type=str, default=os.getenv("GITHUB_TOKEN"), help="GitHub Personal Access Token")
    parser.add_argument("--api-key", type=str, default=os.getenv("LLM_API_KEY"), help="LLM API Key")
    
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub token is required.")
        sys.exit(1)

    # Initialize LLM Client
    if args.api_key:
        llm_client = OpenAILLMClient(api_key=args.api_key)
    else:
        print("No API Key provided, using Mock LLM.")
        llm_client = MockLLMClient()

    # Initialize Service
    service = CodeAgentService(args.token, args.repo, llm_client)
    
    # We might need to ensuring cloning happened if not already handled
    # The service currently relies on explicit calls or existing repo
    # Let's ensure the repo is ready. Service.setup_local_repo() was a placeholder, 
    # but the process_* methods handle cloning if missing.
    
    # ensure we have cloning auth if needed.
    # For now, we assume public repo or token in env for git
    
    if args.pr_number:
        service.process_pr_feedback(args.pr_number)
    elif args.issue_id:
        service.process_issue(args.issue_id)
    else:
        print("Error: Either --issue-id or --pr-number must be provided.")
        sys.exit(1)

if __name__ == "__main__":
    main()
