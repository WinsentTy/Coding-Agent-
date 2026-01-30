import os
import subprocess
from typing import Dict, Optional
from github import Github, Repository, PullRequest
from git import Repo

from shared.llm import LLMClient
from shared.utils import generate_repo_map
from shared.diff_manager import DiffManager

class CodeAgentService:
    def __init__(self, github_token: str, repo_name: str, llm_client: LLMClient):
        self.github_token = github_token
        self.github = Github(github_token)
        self.repo: Repository.Repository = self.github.get_repo(repo_name)
        self.llm_client = llm_client
        self.local_repo_path = os.path.join(os.getcwd(), "workdir")
        self.diff_manager = DiffManager()
    
    def setup_local_repo(self, branch_name: str = "main"):

        """Clones or updates the local repository."""
        if not os.path.exists(os.path.join(self.local_repo_path, ".git")):
            # Note: In a real scenario, handle auth properly in URL
            # For this refactor we assume the environment is set up or token is injected
            # But the original code used logic: f"https://oauth2:{args.token}@github.com/{args.repo}.git"
            # We will rely on caller to set up git auth or use the same logic if passed.
            # However, for simplicity/security, we might assume checkout is done or handled.
            # But let's replicate original logic for now to ensure behavior consistency.
            pass # Logic handled in specific methods or decoupled
            
        repo_git = Repo(self.local_repo_path)
        return repo_git

    def get_feedback_history(self, pr: PullRequest.PullRequest) -> str:
        """Fetches identifying feedback from recent PR comments to build history."""
        comments = list(pr.get_issue_comments())
        if not comments:
            return "No prior feedback."
        
        # Take last 3 comments to provide context without overflowing context window
        history = []
        for c in comments[-3:]:
            history.append(f"--- Comment by {c.user.login} ---\n{c.body}")
        
        return "\n\n".join(history)

    def check_code(self, filename: str) -> Optional[str]:
        """Checks for syntax errors and runs linter. Returns error message or None."""
        # Only check Python files
        if not filename.endswith('.py'):
            return None
            
        # 1. Syntax Check
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read()
            compile(source, filename, 'exec')
        except SyntaxError as e:
            return f"SyntaxError in {filename}: {e}"
        except Exception as e:
            return f"Error reading/compiling {filename}: {e}"

        # 2. Linter Check (Ruff E, F) - optional, skip if ruff not available
        try:
            result = subprocess.run(
                ["ruff", "check", "--select", "E,F", filename], 
                capture_output=True, 
                text=True,
                shell=False 
            )
            if result.returncode != 0:
                # Only fail on actual lint errors, not on ruff exit codes
                if result.stdout.strip():
                    return f"Linter Errors in {filename}:\n{result.stdout}"
        except FileNotFoundError:
            # ruff not installed - skip linting
            print(f"Warning: ruff not found, skipping lint check for {filename}")
        except Exception as e:
            # Other errors - just warn, don't fail
            print(f"Warning: Error running linter on {filename}: {e}")
        
        return None

    def validate_and_fix(self, changes: Dict[str, str], repo_git: Repo) -> bool:
        """Applies changes, validates them, and attempts auto-fix loops."""
        max_retries = 3
        retry_count = 0
        
        print(f"\n=== Validate and Fix ===")
        print(f"Total files in changes: {len(changes)}")
        
        if not changes:
            print("ERROR: No changes to apply!")
            return False
        
        while retry_count < max_retries:
            print(f"\nApplying changes (Attempt {retry_count + 1}/{max_retries})...")
            
            files_with_errors = []
            files_written = 0
            
            # 1. Write Files
            for filename, content in changes.items():
                print(f"\nProcessing file: {filename}")
                full_path = os.path.join(self.local_repo_path, filename)
                
                # Ensure directory exists
                dir_path = os.path.dirname(full_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                # Check for Diff
                final_content = content
                
                # Robustness: If the LLM returned an object instead of a string for the file content
                if isinstance(final_content, dict):
                    # Try to see if it's a nested structure like {"content": "...", "path": "..."}
                    if "content" in final_content:
                        final_content = final_content["content"]
                    else:
                        print(f"Skipping {filename}: content is a dictionary but no 'content' key found.")
                        continue
                
                if not isinstance(final_content, str):
                    print(f"Skipping {filename}: content is not a string ({type(final_content)})")
                    continue

                if "<<<<<< SEARCH" in final_content and os.path.exists(full_path):
                     try:
                         with open(full_path, 'r', encoding='utf-8') as f:
                             original = f.read()
                         final_content = self.diff_manager.apply_diff(original, final_content)
                     except ValueError as e:
                         print(f"Error applying diff to {filename}: {e}")
                         files_with_errors.append((filename, f"Diff Application Error: {e}"))
                         continue
                
                print(f"Writing {len(final_content)} characters to {filename}...")
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
                
                # 2. Check Code
                error = self.check_code(full_path)
                if error:
                    print(f"Validation failed for {filename}: {error}")
                    files_with_errors.append((filename, error))
                else:
                    repo_git.index.add([filename]) # Stage valid files

            # 3. Decision
            if not files_with_errors:
                print("Validation passed!")
                return True
            
            # 4. Fix if errors (Auto-repair)
            retry_count += 1
            if retry_count >= max_retries:
                print("Max validation retries reached.")
                return False
            
            print("Requesting fixes from LLM...")
            # Construct error report
            error_report = "The code has syntax or linter errors:\n"
            for fname, err in files_with_errors:
                error_report += f"File: {fname}\nError: {err}\n"
            
            # We need to pass current (broken) code so LLM sees what it generated
            # For diffs, this is tricky. We should pass the file content AS IT IS ON DISK (broken or partial)
            current_broken_code = {}
            for fname, _ in files_with_errors:
                 # Read from disk
                 full_path = os.path.join(self.local_repo_path, fname)
                 if os.path.exists(full_path):
                     with open(full_path, 'r') as f:
                         current_broken_code[fname] = f.read()
                 else:
                     current_broken_code[fname] = changes.get(fname, "")

            # Ask LLM to fix only broken files
            fixed_changes = self.llm_client.fix_code(current_broken_code, error_report)
            
            # Merge fixes back into main changes dict
            changes.update(fixed_changes)
            
        return False

    def _ensure_local_repo(self) -> Repo:
        """Clones the repository if it doesn't exist, or ensures it's clean."""
        if os.path.exists(self.local_repo_path):
            import shutil
            import stat

            def on_rm_error(func, path, exc_info):
                # path contains the path of the file that couldn't be removed
                # let's try to change the mode and retry
                os.chmod(path, stat.S_IWRITE)
                func(path)

            print(f"Cleaning up existing directory {self.local_repo_path}...")
            shutil.rmtree(self.local_repo_path, onerror=on_rm_error)

        print(f"Cloning repository {self.repo.full_name}...")
        # Use GitHub token for cloning
        auth_url = self.repo.clone_url.replace("https://", f"https://oauth2:{self.github_token}@")
        return Repo.clone_from(auth_url, self.local_repo_path)

    def process_issue(self, issue_id: int):
        """Orchestrates the fix for a specific issue."""
        print(f"Processing Issue #{issue_id}...")
        try:
            issue = self.repo.get_issue(issue_id)
            print(f"Issue title: {issue.title}")
            print(f"Issue body: {issue.body}")
        except Exception as e:
            print(f"Error fetching issue: {e}")
            return

        try:
            repo_git = self._ensure_local_repo()
        except Exception as e:
            print(f"Error preparing repository: {e}")
            return
        
        try:
            repo_map = generate_repo_map(self.local_repo_path)
            print(f"Repository map generated ({len(repo_map)} chars)")
        except Exception as e:
            print(f"Error generating repo map: {e}")
            repo_map = ""

        # Read contents of key files to provide context
        file_contents = ""
        for root, dirs, files in os.walk(self.local_repo_path):
            # Skip hidden directories and common non-code dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.git']]
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.md', '.txt', '.json', '.yaml', '.yml')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.local_repo_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Limit file size in context
                        if len(content) < 5000:
                            file_contents += f"\n\n=== File: {rel_path} ===\n{content}"
                    except Exception:
                        pass
        
        print(f"File contents collected ({len(file_contents)} chars)")
        
        full_context = f"""Repository Structure:
{repo_map}

Current File Contents:
{file_contents}

Task (from Issue):
{issue.body or issue.title}

IMPORTANT: Directly modify the existing files listed above. Do not create new helper scripts."""
        
        print("\n=== Generating Plan ===")
        plan = self.llm_client.generate_plan(full_context)
        print(f"Plan received ({len(plan) if plan else 0} chars):")
        print(plan[:500] if plan else "No plan generated")
        print("...")
        
        print("\n=== Generating Code ===")
        changes = self.llm_client.generate_code(plan)
        print(f"Changes received: {type(changes)}")
        if changes:
            print(f"Files to modify: {list(changes.keys())}")
            for filename, content in changes.items():
                content_preview = str(content)[:200] if content else "None"
                print(f"  - {filename}: {len(str(content)) if content else 0} chars")
                print(f"    Preview: {content_preview}...")
        else:
            print("No changes generated by LLM!")
        
        if not changes:
            print("ERROR: No changes generated. Exiting.")
            return

        # Add timestamp to branch name to avoid conflicts
        import time
        timestamp = int(time.time())
        branch_name = f"feature/issue-{issue_id}-{timestamp}"
        
        print(f"Switching to branch {branch_name}...")
        try:
            current = repo_git.create_head(branch_name)
            current.checkout()
        except Exception:
             repo_git.git.checkout(branch_name)

        if self.validate_and_fix(changes, repo_git):
            print("Committing changes...")
            repo_git.index.commit(f"Fix issue #{issue_id}")
            
            print(f"Pushing branch {branch_name} to origin...")
            try:
                # Use force push to handle existing branches
                repo_git.git.push("origin", branch_name, force=True)
            except Exception as e:
                print(f"Error pushing branch: {e}")
                return

            print("Creating Pull Request...")
            try:
                pr = self.repo.create_pull(
                    title=f"Fix issue #{issue_id}: {issue.title}",
                    body=f"Automated fix for issue #{issue_id}.\n\n{issue.body}",
                    head=branch_name,
                    base=self.repo.default_branch
                )
                print(f"Success! PR created: {pr.html_url}")
            except Exception as e:
                if "A pull request already exists" in str(e):
                    print("Pull Request already exists.")
                else:
                    print(f"Error creating PR: {e}")

    def get_pr_changed_files(self, pr) -> list:
        """
        Fetches the list of files changed in the PR.
        Returns list of file paths.
        """
        try:
            files = list(pr.get_files())
            return [f.filename for f in files if f.status != "removed"]
        except Exception as e:
            print(f"Error fetching PR files: {e}")
            return []

    def process_pr_feedback(self, pr_number: int):
        """Orchestrates the feedback loop for an existing PR."""
        print(f"Processing Feedback for PR #{pr_number}...")
        pr = self.repo.get_pull(pr_number)
        
        # Loop protection
        commits = list(pr.get_commits())
        if len(commits) >= 3:
            print("Max iterations (3) reached. Halting.")
            try:
                pr.create_issue_comment("AI Code Agent: Max repair attempts reached. Please review manually.")
            except Exception:
                pass
            return

        feedback_history = self.get_feedback_history(pr)
        branch_name = pr.head.ref
        
        # Ensure repo
        try:
            repo_git = self._ensure_local_repo()
            repo_git.git.checkout(branch_name)
        except Exception as e:
            print(f"Error preparing repository for PR: {e}")
            return

        # Get changed files from PR dynamically
        print("Fetching changed files from PR...")
        changed_files = self.get_pr_changed_files(pr)
        
        if not changed_files:
            print("No changed files found in PR.")
            return
        
        print(f"Found {len(changed_files)} changed files: {changed_files}")
        
        # Read current content of all changed files
        current_code = {}
        for file_path in changed_files:
            full_path = os.path.join(self.local_repo_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        current_code[file_path] = f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        if not current_code:
            print("Could not read any changed files.")
            return
        
        try:
            repo_map = generate_repo_map(self.local_repo_path)
        except Exception:
            repo_map = ""
        
        # Include file list in context for LLM
        files_context = "\n".join([f"- {f}" for f in changed_files])
        full_feedback = f"""Repository Context:
{repo_map}

Files Changed in PR:
{files_context}

Feedback History:
{feedback_history}"""
        
        changes = self.llm_client.fix_code(current_code, full_feedback)
        
        if self.validate_and_fix(changes, repo_git):
            print("Committing changes...")
            repo_git.index.commit(f"Address feedback for PR #{pr_number}")
            
            print(f"Pushing updates to branch {branch_name}...")
            try:
                repo_git.git.push("origin", branch_name)
                print("Successfully pushed updates.")
            except Exception as e:
                print(f"Error pushing updates: {e}")

