import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional, Dict
from code_agent.service import CodeAgentService
from shared.llm import MockLLMClient, LLMClient
from git import Repo

@dataclass
class BenchmarkTask:
    name: str
    setup_code: Dict[str, str]  # Filename -> Content
    issue_description: str
    verification_function: Callable[[str], bool] # Path -> Success

class Evaluator:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or MockLLMClient()

    def evaluate(self, task: BenchmarkTask) -> bool:
        print(f"Running Benchmark: {task.name}")
        
        # 1. Setup Temp Repo
        temp_dir = tempfile.mkdtemp()
        try:
            # Initialize git 
            repo = Repo.init(temp_dir)
            
            # Write setup code
            for fname, content in task.setup_code.items():
                full_path = os.path.join(temp_dir, fname)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            repo.index.add(list(task.setup_code.keys()))
            repo.index.commit("Initial commit")

            # 2. Initialize Agent
            from unittest.mock import MagicMock, patch
            
            with patch("code_agent.service.Github") as MockGithub:
                 service = CodeAgentService("fake", "fake/repo", self.llm_client)
            
            service.repo = MagicMock()
            service.local_repo_path = temp_dir
            
            mock_issue = MagicMock()
            mock_issue.body = task.issue_description
            mock_issue.title = task.name
            service.repo.get_issue.return_value = mock_issue
            
            # 3. Run Agent
            try:
                service.process_issue(1)
            except SystemExit:
                pass 
            except Exception as e:
                print(f"Agent failed with error: {e}")
                return False

            # 4. Verify
            success = task.verification_function(temp_dir)
            
            # Explicit close
            repo.close()
            return success

        finally:
            # Robust cleanup
            import gc
            gc.collect()
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not clean up temp dir {temp_dir}: {e}")

from typing import Dict
