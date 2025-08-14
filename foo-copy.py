import importlib.util
import os
import sys
import re
import directory_hash  # Import the directory hash module

# Node classes for expression tree
class Node:
    """Base class for all syntax tree nodes"""
    def __init__(self):
        self.result = None
    
    def evaluate(self, executor_func, verify_hash=False, script_hashes=None):
        """To be implemented by subclasses"""
        raise NotImplementedError

class ScriptNode(Node):
    """Node representing a script execution"""
    def __init__(self, name, args=None):
        super().__init__()
        self.name = name
        self.args = args or []
    
    def evaluate(self, executor_func, verify_hash=False, script_hashes=None):
        """Execute the script and return result"""
        expected_hash = script_hashes.get(self.name) if verify_hash and script_hashes else None
        self.result = executor_func(self.name, self.args, verify_hash, expected_hash)
        
        # In logical context, 0 (success) = True, 1 (failure) = False
        logical_result = (self.result == 0)
        
        # Write the result code to stderr for individual script
        sys.stderr.write(f"{self.result}\n")
        
        return logical_result
    
    def __str__(self):
        if self.args:
            return f"({self.name}:{','.join(self.args)})"
        return f"({self.name})"

class LogicalOperatorNode(Node):
    """Node representing a logical operator with children"""
    def __init__(self, operator, children=None):
        super().__init__()
        self.operator = operator
        self.children = children or []
    
    def add_child(self, child):
        self.children.append(child)
    
    def __str__(self):
        children_str = ", ".join(str(child) for child in self.children)
        return f"{self.operator} [ {children_str} ]"

class NotNode(Node):
    """Node representing a NOT operator"""
    def __init__(self, child=None):
        super().__init__()
        self.child = child
    
    def evaluate(self, executor_func, verify_hash=False, script_hashes=None):
        """Evaluate NOT node by inverting the result of its child"""
        if self.child is None:
            print("Warning: NOT operator with no child")
            return False
            
        child_result = self.child.evaluate(executor_func, verify_hash, script_hashes)
        result = not child_result
        
        print(f"NOT operator: inverting {child_result} to {result}")
        self.result = result
        return result
    
    def __str__(self):
        return f"!{self.child}"

class AndNode(LogicalOperatorNode):
    """Node representing an AND operator"""
    def __init__(self, circuit_breaking=True, children=None):
        super().__init__("&&" if circuit_breaking else "&", children)
        self.circuit_breaking = circuit_breaking
    
    def evaluate(self, executor_func, verify_hash=False, script_hashes=None):
        """Evaluate AND node with or without circuit breaking"""
        result = True
        
        for child in self.children:
            child_result = child.evaluate(executor_func, verify_hash, script_hashes)
            
            if not child_result:
                result = False
                # Circuit breaking: if any child is false, stop evaluation
                if self.circuit_breaking:
                    print(f"Circuit breaking AND: stopping at first FALSE result")
                    break
        
        self.result = result
        return result

class OrNode(LogicalOperatorNode):
    """Node representing an OR operator"""
    def __init__(self, circuit_breaking=True, children=None):
        super().__init__("||" if circuit_breaking else "|", children)
        self.circuit_breaking = circuit_breaking
    
    def evaluate(self, executor_func, verify_hash=False, script_hashes=None):
        """Evaluate OR node with or without circuit breaking"""
        result = False
        
        for child in self.children:
            child_result = child.evaluate(executor_func, verify_hash, script_hashes)
            
            if child_result:
                result = True
                # Circuit breaking: if any child is true, stop evaluation
                if self.circuit_breaking:
                    print(f"Circuit breaking OR: stopping at first TRUE result")
                    break
        
        self.result = result
        return result

def validate_expression_format(expression):
    """Basic validation of expression format. Returns True if valid, False otherwise."""
    # Check balanced brackets and parentheses
    if expression.count('[') != expression.count(']'):
        return False
    if expression.count('(') != expression.count(')'):
        return False
    
    # Check for operators without brackets
    for op in ["&&", "||", "&", "|"]:
        i = 0
        while i < len(expression):
            i = expression.find(op, i)
            if i == -1:
                break
                
            # Skip if part of another operator
            if op in ["&", "|"] and i+1 < len(expression) and expression[i+1] == expression[i]:
                i += 1
                continue
            
            # Find next non-whitespace character
            j = i + len(op)
            while j < len(expression) and expression[j].isspace():
                j += 1
                
            if j >= len(expression) or expression[j] != '[':
                return False
                
            i += len(op)
    
    return True

# Parser functions
def parse_logical_expression(expression):

    """Parse a logical expression string into a syntax tree."""
    # Validate basic expression format first
    if not validate_expression_format(expression):
        print("Error in expression format.")
        print("\nPlease use one of these formats:")
        print("  (A)                    - Simple script")
        print("  (A:arg1,arg2)          - Script with arguments")
        print("  && [ (A), (B) ]        - AND operator")
        print("  || [ (A), (B) ]        - OR operator") 
        print("  !(A)                   - NOT operator")
        print("  || [ && [ (A), (B) ], !(C) ]  - Complex expression")
        print("  (A:\"x,y\")             - Quoted argument (keeps x,y together as one argument)")
        print("  (A:\"x,y\",arg2)         - x,y as arg1 and regular arg2")
        print("  (A:\"\\\"x\\\"\")      - To include quotes as part of the argument ")
        return None

    # First normalize the spacing but preserve spaces between commas
    expression = re.sub(r'\s*\[\s*', ' [ ', expression)
    expression = re.sub(r'\s*\]\s*', ' ] ', expression)
    expression = re.sub(r'\s*\(\s*', ' ( ', expression)
    expression = re.sub(r'\s*\)\s*', ' ) ', expression)
    expression = re.sub(r'\s*,\s*', ', ', expression)
    expression = re.sub(r'\s+', ' ', expression).strip()
    
    # Print the normalized expression to help debug
    # print(f"Normalized expression: {expression}")
    
    # Parse the expression
    node, pos = _parse_expression(expression, 0)
    
    # Make sure we consumed the entire expression
    if pos < len(expression):
        print(f"Warning: Expression parsing stopped at position {pos}/{len(expression)}. Remainder: '{expression[pos:]}'")
    
    return node

def _parse_expression(expr, pos):
    """Recursive function to parse a logical expression."""
    # Skip whitespace
    while pos < len(expr) and expr[pos].isspace():
        pos += 1
    
    if pos >= len(expr):
        return None, pos
    
    # Check for NOT operator
    if expr[pos] == "!":
        node = NotNode()
        pos += 1  # Skip the ! character
        
        # Skip whitespace after !
        while pos < len(expr) and expr[pos].isspace():
            pos += 1
            
        # Parse the child expression
        if pos < len(expr):
            child, pos = _parse_expression(expr, pos)
            if child:
                node.child = child
            else:
                print("Warning: Missing expression after NOT operator")
        else:
            print("Warning: Missing expression after NOT operator")
            
        return node, pos
    # Check for operator type
    elif expr[pos:pos+2] == "&&":
        # Circuit-breaking AND
        node = AndNode(circuit_breaking=True)
        pos = _parse_operator_children(expr, pos+2, node)
        return node, pos
    elif expr[pos:pos+2] == "||":
        # Circuit-breaking OR
        node = OrNode(circuit_breaking=True)
        pos = _parse_operator_children(expr, pos+2, node)
        return node, pos
    elif expr[pos] == "&" and (pos+1 >= len(expr) or expr[pos+1] != "&"):
        # Normal AND
        node = AndNode(circuit_breaking=False)
        pos = _parse_operator_children(expr, pos+1, node)
        return node, pos
    elif expr[pos] == "|" and (pos+1 >= len(expr) or expr[pos+1] != "|"):
        # Normal OR
        node = OrNode(circuit_breaking=False)
        pos = _parse_operator_children(expr, pos+1, node)
        return node, pos
    elif expr[pos] == "(":
        # Script node with parentheses
        return _parse_script_node(expr, pos)
    else:
        # This should not happen with the new format that requires parentheses
        print(f"Warning: Unexpected character at position {pos}: '{expr[pos]}'")
        # Try to recover by looking for the next recognizable token
        while pos < len(expr) and expr[pos] not in "()[],&|":
            pos += 1
        return None, pos

def _parse_script_node(expr, pos):
    """Parse a script node with exact format (Name) or (Name:arg1,arg2)."""
    # Skip the opening parenthesis
    pos += 1
    
    # Find the end of the script part (either at : or ))
    colon_pos = expr.find(':', pos)
    close_pos = expr.find(')', pos)
    
    if colon_pos != -1 and colon_pos < close_pos:
        # Has arguments
        script_name = expr[pos:colon_pos].strip()
        args_str = expr[colon_pos+1:close_pos].strip()
        
        # Parse arguments with proper handling of quotes
        args = []
        if args_str:
            i = 0
            current_arg = []
            in_quotes = False
            
            while i < len(args_str):
                char = args_str[i]
                
                # Handle escaped characters
                if char == '\\' and i + 1 < len(args_str):
                    current_arg.append(args_str[i+1])
                    i += 2
                    continue
                
                # Handle quotes
                elif char == '"':
                    in_quotes = not in_quotes
                    current_arg.append(char)  # Keep quotes in the argument for now
                    i += 1
                    continue
                
                # Handle commas outside quotes
                elif char == ',' and not in_quotes:
                    arg_str = ''.join(current_arg).strip()
                    # Strip surrounding quotes if present
                    if arg_str.startswith('"') and arg_str.endswith('"') and len(arg_str) >= 2:
                        arg_str = arg_str[1:-1]  # Remove surrounding quotes
                    args.append(arg_str)
                    current_arg = []
                    i += 1
                    continue
                
                # Regular character
                else:
                    current_arg.append(char)
                    i += 1
            
            # Add the last argument
            if current_arg:
                arg_str = ''.join(current_arg).strip()
                # Strip surrounding quotes if present
                if arg_str.startswith('"') and arg_str.endswith('"') and len(arg_str) >= 2:
                    arg_str = arg_str[1:-1]  # Remove surrounding quotes
                args.append(arg_str)
        
        pos = close_pos + 1
    else:
        # No arguments
        script_name = expr[pos:close_pos].strip()
        args = []
        pos = close_pos + 1
        
    return ScriptNode(script_name, args), pos

def _parse_operator_children(expr, pos, node):
    """Parse children of a logical operator."""
    # Skip whitespace
    while pos < len(expr) and expr[pos].isspace():
        pos += 1
    
    # Check for opening bracket
    if pos < len(expr) and expr[pos] == "[":
        pos += 1  # Skip opening bracket
        
        # Parse children until closing bracket
        while pos < len(expr) and expr[pos] != "]":
            # Skip whitespace and commas
            while pos < len(expr) and (expr[pos].isspace() or expr[pos] == ","):
                pos += 1
            
            # Check if we're at the end of children
            if pos < len(expr) and expr[pos] != "]":
                child, pos = _parse_expression(expr, pos)
                if child:
                    node.add_child(child)
            else:
                break
        
        # Skip closing bracket
        if pos < len(expr) and expr[pos] == "]":
            pos += 1
        else:
            print(f"Warning: Missing closing bracket for operator '{node.operator}'")
    else:
        print(f"Warning: Missing opening bracket for operator '{node.operator}'")
    
    return pos

def collect_script_names_from_tree(node):
    """Recursively collect all script names from an expression tree."""
    if isinstance(node, ScriptNode):
        return [node.name]
    elif isinstance(node, NotNode):
        return collect_script_names_from_tree(node.child) if node.child else []
    elif isinstance(node, LogicalOperatorNode):
        names = []
        for child in node.children:
            names.extend(collect_script_names_from_tree(child))
        return names
    return []

def dynamic_import_and_run(script_name, args, verify_hash=False, expected_hash=None):
    """
    Import and run a script module.
    
    Args:
        script_name: Name of the script (also the folder name)
        args: List of arguments to pass to the script function
        verify_hash: Whether to verify the directory hash
        expected_hash: Expected hash value (if verifying)
        
    Returns:
        0 for success, 1 for failure
    """
    # Get the absolute path to the script folder
    script_folder = os.path.join(os.getcwd(), script_name)
    script_path = os.path.join(script_folder, f"{script_name}.py")
    
    # First check if the script folder exists
    if not os.path.isdir(script_folder):
        result = 1  # Failure
        print(f"Error: Script folder '{script_folder}' not found")
        print(f"=== FAILED {script_name} ({result}) ===\n")
        return result
    
    # Verify hash if requested
    if verify_hash and expected_hash is not None:
        # Exclude __pycache__ directories by default
        exclude_dirs = ['__pycache__', '.git', '.vscode']
        if not directory_hash.verify_directory_hash(script_folder, expected_hash, exclude_dirs, verbose=False):
            result = 1  # Failure
            print(f"=== FAILED {script_name} ({result}) ===\n")
            return result
    
    # Check if the actual script file exists
    if not os.path.exists(script_path):
        result = 1  # Failure
        print(f"Error: Script {script_path} not found")
        print(f"=== FAILED {script_name} ({result}) ===\n")
        return result
        
    # Load the module
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    module = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        result = 1  # Failure
        print(f"Error loading {script_name}: {e}")
        print(f"=== FAILED {script_name} ({result}) ===\n")
        return result

    print(f"\n=== STARTING {script_name} ===")
    try:
        # Check if the function with the expected name exists
        if not hasattr(module, script_name):
            print(f"Error: Function '{script_name}()' not found in module")
            print(f"=== FAILED {script_name} (1) ===\n")
            return 1  # Return failure
        
        func = getattr(module, script_name)
            
        # Print script arguments for debugging
        # if args:
        #     print(f"Running with arguments: {args}")
            
        func_return = func(*args)
        # If we get here, the function completed without errors
        result = 0  # Success
        print(f"Function returned: {func_return}")
        print(f"=== FINISHED {script_name} ({result}) ===\n")
        return result
    except Exception as e:
        result = 1  # Failure
        print(f"Error running {script_name}: {e}")
        print(f"=== FAILED {script_name} ({result}) ===\n")
        return result

def main():
    if len(sys.argv) < 3:
        print("Usage: python foo.py <log_id> \"|| [ && [ (A:hello,world), (B) ], && [ (C:test), (D), (E:2,4) ] ]\"")
        print("  NEW: The NOT operator is supported with ! symbol: \"! (A)\" or \"! && [ (A), (B) ]\"")
        sys.stderr.write("1\n")
        sys.exit(1)
        return

    log_id = sys.argv[1]
    expression_string = sys.argv[2]
    
    # Script hashes for verification
    script_hashes = {
        "A": "6c8c069a22d96be8a18c21722cdac82d", 
        "B": "efa8b2f56b3c0c5414e8bf6f91da1dd5",
        "C": "d1a041a123788ac2406389c107512f1d",
        "D": "32453a3fda76985d04905378d172f3ce",
        "E": "2861031a067f87fdb0d2bb7ebf0bd679"
        # Add other script hashes here after generating them with:
    }

    print(f"Log ID: {log_id}")
    
    # Parse the expression string into a logical tree
    expression_tree = parse_logical_expression(expression_string)
    
    # Check if parsing was successful
    if expression_tree is None:
        print("Invalid expression format. Please fix and try again.")
        sys.stderr.write("1\n")
        sys.exit(1)
    
    # STEP 1: Collect all script names in the expression tree
    script_names = collect_script_names_from_tree(expression_tree)
    script_names = list(set(script_names))  # Remove duplicates
    print(f"\n=== PRE-VERIFICATION OF SCRIPT HASHES ===")
    print(f"Scripts to verify: {', '.join(script_names)}")
    
    # STEP 2: Verify all script hashes before executing any script
    verify_hash = True  # Always verify hash if available
    if verify_hash:
        all_hashes_valid = True
        
        for script_name in script_names:
            # Get the absolute path to the script folder
            script_folder = os.path.join(os.getcwd(), script_name)
            
            # Check if the script folder exists
            if not os.path.isdir(script_folder):
                print(f"Error: Script folder '{script_folder}' not found")
                all_hashes_valid = False
                break  # Stop at first failure
            
            # Get expected hash if available
            expected_hash = script_hashes.get(script_name)
            
            # If we have an expected hash, verify it
            if expected_hash is not None:
                print(f"Verifying hash for {script_name}...", end=" ")
                
                # Exclude __pycache__ directories by default
                exclude_dirs = ['__pycache__', '.git', '.vscode']
                actual_hash = directory_hash.calculate_directory_hash(script_folder, exclude_dirs, verbose=False)
                
                if actual_hash != expected_hash:
                    print("FAILED")
                    print(f"Hash verification FAILED for {script_folder}")
                    print(f"  Expected: {expected_hash}")
                    print(f"  Actual:   {actual_hash}")
                    all_hashes_valid = False
                    break  # Stop at first failure
                else:
                    print("PASSED")
            else:
                # NEW: No hash available is now considered a failure
                print(f"Verifying hash for {script_name}... FAILED")
                print(f"No hash available for script '{script_name}'")
                print(f"All scripts must have a hash defined for verification.")
                all_hashes_valid = False
                break  # Stop at first failure
        
        # If any hash verification failed, exit immediately
        if not all_hashes_valid:
            print("\n=== HASH VERIFICATION FAILED ===")
            print("Execution aborted: Fix the script directories and try again.")
            sys.stderr.write("1\n")
            sys.exit(1)
        
        print("All script hashes verified successfully.")
        print("=== PRE-VERIFICATION COMPLETE ===\n")
    
    # Execute the logical expression
    logical_result = expression_tree.evaluate(
        dynamic_import_and_run, 
        False,  # No need to verify hash during execution since we already did
        script_hashes
    )
    
    # Convert boolean result to exit code (True=0, False=1)
    final_code = 0 if logical_result else 1
    
    # Print summary of the logical result
    print("\nLogical Expression Result:", "Success (True)" if logical_result else "Failure (False)")
    print(f"Final result code to return: {final_code}")
    
    # Write final result code to stderr
    sys.stderr.write(f"{final_code}\n")
    
    sys.exit(final_code)

if __name__ == "__main__":
    main()