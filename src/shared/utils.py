import os
import ast

def get_python_summary(file_path):
    """Parses a Python file and returns a summary of classes and functions."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception:
        return "    (Error parsing Python file)"

    summary = []
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            summary.append(f"    class {node.name}:")
            if ast.get_docstring(node):
                doc = ast.get_docstring(node).strip().split('\n')[0]
                summary.append(f"      \"\"\"{doc}...\"\"\"")
            # Determine methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    args = [a.arg for a in item.args.args]
                    summary.append(f"      def {item.name}({', '.join(args)}):")
        elif isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            summary.append(f"    def {node.name}({', '.join(args)}):")
            if ast.get_docstring(node):
                doc = ast.get_docstring(node).strip().split('\n')[0]
                summary.append(f"      \"\"\"{doc}...\"\"\"")

    return "\n".join(summary)

def generate_repo_map(root_dir, ignore_dirs=None, max_chars=4000):
    """
    Generates a text-based tree view of the repository with Python summaries.
    Stops if the output exceeds max_chars to preserve context window.
    """
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'venv', '.env', '.mypy_cache', '.pytest_cache'}

    repo_map = []
    total_chars = 0

    for root, from_dirs, files in os.walk(root_dir):
        # Filter directories in-place
        from_dirs[:] = [d for d in from_dirs if d not in ignore_dirs]
        
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        
        dir_line = f"{indent}{os.path.basename(root)}/"
        repo_map.append(dir_line)
        total_chars += len(dir_line) + 1
        
        if total_chars > max_chars:
            repo_map.append(f"{indent}... (Truncated due to size limit)")
            return "\n".join(repo_map)

        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            file_path = os.path.join(root, f)
            file_line = f"{sub_indent}{f}"
            
            repo_map.append(file_line)
            total_chars += len(file_line) + 1
            
            if total_chars > max_chars:
                repo_map.append(f"{sub_indent}... (Truncated)")
                return "\n".join(repo_map)
            
            if f.endswith(".py"):
                summary = get_python_summary(file_path)
                if summary:
                    # Check if adding summary exceeds limit
                    if total_chars + len(summary) > max_chars:
                         repo_map.append(f"{sub_indent}  (Summary truncated)")
                         # We could continue to list files but skip summaries, but let's just stop to be safe
                         return "\n".join(repo_map)
                    
                    repo_map.append(summary)
                    total_chars += len(summary) + 1
    
    return "\n".join(repo_map)
