import os
from tests.evaluation.benchmark import BenchmarkTask

def verify_typo_fix(repo_path: str) -> bool:
    file_path = os.path.join(repo_path, "main.py")
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r") as f:
        content = f.read()
    return "print('Hello World')" in content and "print('Hello Workd')" not in content

TYPO_TASK = BenchmarkTask(
    name="Fix Typo",
    setup_code={
        "main.py": "def main():\n    print('Hello Workd')\n\nif __name__ == '__main__':\n    main()\n"
    },
    issue_description="Fix the typo 'Workd' to 'World' in main.py",
    verification_function=verify_typo_fix
)

ALL_TASKS = [TYPO_TASK]
