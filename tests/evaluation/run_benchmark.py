from tests.evaluation.benchmark import Evaluator
from tests.evaluation.tasks import ALL_TASKS
from shared.llm import MockLLMClient
from typing import Dict

class SmartMockLLM(MockLLMClient):
    """
    A smarter mock that actually fixes the specific benchmark task 
    to prove the evaluation infrastructure works.
    """
    def generate_plan(self, context: str) -> str:
        return "1. detailed plan to fix typo"

    def generate_code(self, plan: str) -> Dict[str, str]:
        # Detect task based on context (in real life) or just return the fix for the known task
        # Since this is a specialized mock for the 'Fix Typo' task:
        return {
            "main.py": """<<<<<< SEARCH
    print('Hello Workd')
======
    print('Hello World')
>>>>>> REPLACE"""
        }

def main():
    # Use our Smart Mock for the benchmark
    evaluator = Evaluator(llm_client=SmartMockLLM())
    
    results = {}
    for task in ALL_TASKS:
        success = evaluator.evaluate(task)
        results[task.name] = "PASS" if success else "FAIL"
    
    print("\nBenchmark Results:")
    for name, status in results.items():
        print(f"{name}: {status}")

if __name__ == "__main__":
    main()
