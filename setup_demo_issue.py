import argparse
import os
import sys
from github import Github

def main():
    parser = argparse.ArgumentParser(description="Create a demo issue for Coding Agents")
    parser.add_argument("--repo", type=str, required=True, help="Repository name (owner/repo)")
    parser.add_argument("--token", type=str, default=os.getenv("GITHUB_TOKEN"), help="GitHub Personal Access Token")
    
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub token is required.")
        sys.exit(1)

    print(f"Connecting to {args.repo}...")
    try:
        gh = Github(args.token)
        repo = gh.get_repo(args.repo)
    except Exception as e:
        print(f"Error connecting to repo: {e}")
        sys.exit(1)

    title = "Demo: Fix typo in backend"
    body = """
    We have a typo in our logging message.
    
    Please fix 'Startign server...' to 'Starting server...' in `src/backend.py` (or create it if missing).
    
    This is a test issue for the Code Agent.
    """

    print("Creating issue...")
    try:
        issue = repo.create_issue(title=title, body=body)
        print(f"Success! Issue created: {issue.html_url}")
        print(f"Issue ID: {issue.number}")
    except Exception as e:
        print(f"Error creating issue: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
