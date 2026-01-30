import re

class DiffManager:
    """
    Manages application of partial code changes using Search/Replace blocks.
    
    Expected format:
    <<<<<< SEARCH
    original code line 1
    original code line 2
    ======
    new code line 1
    new code line 2
    >>>>>> REPLACE
    """
    
    def apply_diff(self, original_content: str, diff_content: str) -> str:
        """
        Applies search/replace blocks to the original content.
        Returns the modified content.
        Raises ValueError if a block cannot be applied.
        """
        pattern = re.compile(
            r'<<<<<< SEARCH\n(.*?)\n======\n(.*?)\n>>>>>> REPLACE', 
            re.DOTALL
        )
        
        matches = list(pattern.finditer(diff_content))
        
        if not matches:
            # Fallback: if no blocks found, assume full file replacement if safe?
            # Or maybe just return original if really nothing matched?
            # For this implementation, let's strictly require blocks or assume it's a full replacement 
            # ONLY if it doesn't look like a diff attempt.
            # But the plan says "expect partial updates". 
            # Let's assume if no blocks, we fallback to treating input as full content 
            # IF it doesn't contain markers.
            if "<<<<<< SEARCH" not in diff_content:
                 return diff_content # Treat as full replacement
            return original_content

        modified_content = original_content
        
        for match in matches:
            search_block = match.group(1)
            replace_block = match.group(2)
            
            # Check for exact match
            if search_block in modified_content:
                # Ensure unique match? For now, replace first occurrence
                count = modified_content.count(search_block)
                if count > 1:
                     raise ValueError(f"Search block matches {count} times. Ambiguous update.")
                modified_content = modified_content.replace(search_block, replace_block, 1)
            else:
                 # Fuzzy match could go here (stripping whitespace)
                 # For now, strict.
                 raise ValueError(f"Search block not found in content:\n{search_block}")
                 
        return modified_content
