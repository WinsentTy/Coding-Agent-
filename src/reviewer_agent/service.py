import subprocess
import re
import json
import shlex
import requests
from typing import Optional, List, Dict, Any
from github import Github, Repository

from shared.llm import LLMClient


class ReviewerService:
    def __init__(self, github_token: str, repo_name: str, llm_client: LLMClient):
        self.github_token = github_token
        self.github = Github(github_token)
        self.repo: Repository.Repository = self.github.get_repo(repo_name)
        self.llm_client = llm_client

    def run_linter(self, command: str) -> str:
        """Runs a linter command and returns its output."""
        try:
            args = shlex.split(command)
            result = subprocess.run(
                args, 
                capture_output=True, 
                text=True, 
                shell=False 
            )
            # Combine stdout and stderr
            return f"Command: {command}\nExit Code: {result.returncode}\nOutput:\n{result.stdout}\n{result.stderr}\n"
        except Exception as e:
            return f"Error running {command}: {e}\n"

    def get_linked_issue_number(self, pr_body: str) -> Optional[int]:
        """Extracts the first linked issue number from PR body (e.g., 'Closes #123')."""
        if not pr_body:
            return None
        match = re.search(r'#(\d+)', pr_body)
        return int(match.group(1)) if match else None

    def get_ci_jobs_status(self, pr) -> Dict[str, Any]:
        """
        Fetches the status of CI jobs (GitHub Checks) for the PR's head commit.
        Returns a structured dict with overall status and individual check details.
        """
        try:
            # Get the latest commit on the PR
            commits = list(pr.get_commits())
            if not commits:
                return {"status": "unknown", "checks": [], "summary": "No commits found."}
            
            head_commit = commits[-1]
            
            # Get check runs for the commit
            check_runs = list(head_commit.get_check_runs())
            
            checks_info: List[Dict[str, Any]] = []
            failed_checks: List[str] = []
            pending_checks: List[str] = []
            
            for check in check_runs:
                check_info = {
                    "name": check.name,
                    "status": check.status,
                    "conclusion": check.conclusion,
                    "url": check.html_url
                }
                checks_info.append(check_info)
                
                if check.status != "completed":
                    pending_checks.append(check.name)
                elif check.conclusion not in ("success", "skipped", "neutral"):
                    failed_checks.append(f"{check.name}: {check.conclusion}")
            
            # Determine overall status
            if pending_checks:
                overall_status = "pending"
                summary = f"Pending checks: {', '.join(pending_checks)}"
            elif failed_checks:
                overall_status = "failed"
                summary = f"Failed checks: {', '.join(failed_checks)}"
            elif checks_info:
                overall_status = "success"
                summary = f"All {len(checks_info)} checks passed."
            else:
                overall_status = "no_checks"
                summary = "No CI checks configured for this repository."
            
            return {
                "status": overall_status,
                "checks": checks_info,
                "summary": summary,
                "failed": failed_checks,
                "pending": pending_checks
            }
            
        except Exception as e:
            print(f"Error fetching CI status: {e}")
            return {"status": "error", "checks": [], "summary": f"Error: {e}"}

    def get_pr_diff(self, pr) -> str:
        """Fetches the actual diff content from the PR."""
        try:
            # Use requests to fetch the diff directly
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3.diff"
            }
            response = requests.get(pr.diff_url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Failed to fetch diff: {response.status_code}")
                return f"(Could not fetch diff: HTTP {response.status_code})"
        except Exception as e:
            print(f"Error fetching diff: {e}")
            return f"(Error fetching diff: {e})"

    def process_pr_review(self, pr_number: int, pr_body: str = ""):
        """Orchestrates the PR review process."""
        print(f"Starting Review for PR #{pr_number}...")
        
        try:
            pr = self.repo.get_pull(pr_number)
            if not pr_body:
                pr_body = pr.body or ""
        except Exception as e:
            print(f"Error fetching PR: {e}")
            return

        # 1. Get Diff
        print("Fetching diff...")
        diff_text = self.get_pr_diff(pr)

        # 2. Get Linked Issue
        issue_number = self.get_linked_issue_number(pr_body)
        issue_text = "No linked issue found."
        if issue_number:
            try:
                issue = self.repo.get_issue(issue_number)
                issue_text = f"Title: {issue.title}\nBody: {issue.body}"
            except Exception as e:
                print(f"Error fetching linked issue #{issue_number}: {e}")
        
        # 3. Check CI Jobs Status
        print("Checking CI jobs status...")
        ci_status = self.get_ci_jobs_status(pr)
        ci_summary = ci_status["summary"]
        
        # 4. Run Linters
        print("Running linters...")
        linter_output = ""
        linter_output += self.run_linter("ruff check .")
        linter_output += self.run_linter("mypy .")
        
        # 5. LLM Review (include CI status in analysis)
        print("Analysing with LLM...")
        full_linter_output = f"=== CI Pipeline Status ===\n{ci_summary}\n\n=== Local Linter Results ===\n{linter_output}"
        review_result = self.llm_client.review_pr(issue_text, diff_text, full_linter_output)
        
        # Add CI info to review result
        review_result["ci_status"] = ci_status["status"]
        review_result["ci_summary"] = ci_summary
        
        # 6. Build Comment
        ci_status_emoji = {
            "success": "✅",
            "failed": "❌",
            "pending": "⏳",
            "no_checks": "⚪",
            "unknown": "❓",
            "error": "⚠️"
        }.get(ci_status["status"], "❓")
        
        comment_body = f"""## AI Review: {review_result['status']}

### CI Pipeline Status: {ci_status_emoji} {ci_status['status'].upper()}
{ci_summary}

<details>
<summary>CI Check Details</summary>

| Check | Status | Conclusion |
|-------|--------|------------|
"""
        for check in ci_status.get("checks", []):
            comment_body += f"| {check['name']} | {check['status']} | {check.get('conclusion', 'N/A')} |\n"
        
        comment_body += f"""
</details>

<details>
<summary>Local Linter Results</summary>

```
{linter_output}
```
</details>

### Structured Feedback
```json
{json.dumps(review_result, indent=2)}
```
"""
        # 7. Post Comment to PR
        print("Posting comment to PR...")
        try:
            pr.create_issue_comment(comment_body)
            print(f"Successfully posted review comment to PR #{pr_number}")
        except Exception as e:
            print(f"Error posting comment: {e}")
            print(f"--- COMMENT PREVIEW ---\n{comment_body}\n-----------------------")
