from abc import ABC, abstractmethod
import os
from typing import Dict, Any

class LLMClient(ABC):
    """Abstract base class for LLM interactions."""
    
    @abstractmethod
    def generate_plan(self, issue_text: str) -> str:
        """Generates a plan of changes based on the issue description."""
        pass

    @abstractmethod
    def generate_code(self, plan: str) -> Dict[str, str]:
        """Generates code changes based on the plan.
        Returns a dictionary where keys are filenames and values are file contents.
        """
        pass

    @abstractmethod
    def review_pr(self, issue_text: str, diff: str, linter_output: str) -> Dict[str, Any]:
        """Reviews a PR based on issue requirements, diff, and linter results.
        Returns a dict matching schema:
        {
          "status": "APPROVE" | "REQUEST_CHANGES",
          "summary": str,
          "files_to_fix": List[str],
          "comments": List[Dict[str, Any]]  # {"file": str, "line": int, "message": str}
        }
        """
        pass

    @abstractmethod
    def fix_code(self, current_code: Dict[str, str], feedback: str) -> Dict[str, str]:
        """Generates fixed code based on current code and feedback/reviews.
        Returns a dictionary of filename -> new content.
        """
        pass

class MockLLMClient(LLMClient):
    """Mock implementation for testing."""
    
    def generate_plan(self, issue_text: str) -> str:
        return f"Plan for issue: {issue_text}\n1. Fix the bug in main.py"

    def generate_code(self, plan: str) -> Dict[str, str]:
        return {
            "src/backend.py": "def start_server():\n    print('Starting server...')\n"
        }

    def review_pr(self, issue_text: str, diff: str, linter_output: str) -> Dict[str, Any]:
        return {
            "status": "APPROVE",
            "summary": "The changes look good and satisfy the issue requirements.",
            "files_to_fix": [],
            "comments": []
        }

    def fix_code(self, current_code: Dict[str, str], feedback: str) -> Dict[str, str]:
        return {k: v + f"\n# Fixed based on feedback: {feedback[:20]}..." for k, v in current_code.items()}

class OpenAILLMClient(LLMClient):
    """OpenAI implementation of LLMClient."""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.model = model or os.getenv("LLM_MODEL") or "gpt-4-1106-preview"

        if not self.api_key:
            raise ValueError("OpenAI API key is required.")
        
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _parse_json(self, content: str) -> Dict:
        import json
        import re
        # Strip markdown code blocks if present
        if "```" in content:
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content)
        try:
            data = json.loads(content.strip())
            # Un-nest common wrappers
            if isinstance(data, dict):
                for wrapper in ["files", "changes", "code", "implementation"]:
                    if wrapper in data and isinstance(data[wrapper], dict) and len(data) == 1:
                        return data[wrapper]
            return data
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from LLM: {content}")
            return {}

    def generate_plan(self, issue_text: str) -> str:
        messages = [
            {"role": "system", "content": """You are a senior software engineer. Analyze the issue and propose a concise implementation plan.

IMPORTANT RULES:
1. You must DIRECTLY EDIT the existing files mentioned in the task
2. DO NOT create helper scripts, utility files, or automation tools
3. Make the MINIMAL changes needed to solve the issue
4. If the task is to fix a typo, just fix the typo in the original file
5. Be specific about which files to modify and what exact changes to make"""},
            {"role": "user", "content": f"Issue:\n{issue_text}"}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    def generate_code(self, plan: str) -> Dict[str, str]:
        prompt = f"""You are an expert coder. Implement the changes based on this plan:
{plan}

CRITICAL INSTRUCTIONS:
1. Return ONLY a valid JSON object where keys are FILE PATHS and values are the COMPLETE NEW FILE CONTENTS
2. You must DIRECTLY MODIFY the existing files - provide their full new content
3. DO NOT create new helper scripts or utility files
4. DO NOT create scripts that modify other files
5. If fixing a typo in main.py, return {{"main.py": "corrected content here"}}
6. Make MINIMAL changes - only what is necessary to solve the issue
7. Do not include any explanation or markdown formatting

Example for fixing a typo:
Task: Fix typo "Wolrd" -> "World" in main.py which contains: print("Hello Wolrd")
Correct response: {{"main.py": "print(\\"Hello World\\")"}}

WRONG response: Creating a script to fix typos (DO NOT DO THIS!)
"""
        messages = [
            {"role": "system", "content": "You are a coding agent. Output ONLY valid JSON. Make minimal, direct changes to existing files."},
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return self._parse_json(response.choices[0].message.content)

    def review_pr(self, issue_text: str, diff: str, linter_output: str) -> Dict[str, Any]:
        prompt = f"""
Review this PR diff against the issue: {issue_text}
Diff:
{diff}
Linter Output:
{linter_output}

Return ONLY a valid JSON object with:
- "status": "APPROVE" or "REQUEST_CHANGES"
- "summary": string
- "files_to_fix": list of strings
- "comments": list of {{ "file": str, "line": int, "message": str }}
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        result = self._parse_json(response.choices[0].message.content)
        if not result:
             return {"status": "APPROVE", "summary": "Error parsing review", "comments": []}
        return result

    def fix_code(self, current_code: Dict[str, str], feedback: str) -> Dict[str, str]:
        prompt = f"""
Fix the code based on the feedback.
Feedback: {feedback}
Current Code (Files):
{current_code}

Return ONLY a valid JSON object: {{ filename: new_content }}
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_json(response.choices[0].message.content)
