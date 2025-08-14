import os
import hashlib

def calculate_directory_hash(directory_path, exclude_dirs=None, verbose=True):
    """
    Calculate a deterministic hash of an entire directory structure.
    
    Args:
        directory_path (str): Path to the directory to hash
        exclude_dirs (list): List of directory names to exclude (e.g., ['__pycache__', '.git'])
        verbose (bool): Whether to print detailed hashing information
        
    Returns:
        str: MD5 hash of the directory as a hexadecimal string, or None if directory doesn't exist
    Features:
        - Sensitive to directory structure (folder hierarchy)
        - Sensitive to file contents
        - Insensitive to file access times, order of these files and other metadata    
    """
    if not os.path.exists(directory_path):
        return None
    
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', '.vscode']
    
    if verbose:
        print(f"Calculating hash for directory: {directory_path}")
    
    # Store both file hashes and structure information
    directory_entries = []
    
    # Walk through the directory structure
    for root, dirs, files in os.walk(directory_path):
        # Exclude directories we want to skip
        for exclude_dir in exclude_dirs:
            if exclude_dir in dirs:
                dirs.remove(exclude_dir)
        
        # Sort directories for consistent traversal
        dirs.sort()
        
        # Include directory structure in the hash
        rel_dir_path = os.path.relpath(root, directory_path)
        if rel_dir_path != '.':  # Skip the root directory itself
            # Add entry for this directory to capture the tree structure
            dir_entry = f"DIR:{rel_dir_path}"
            directory_entries.append(dir_entry)
            if verbose:
                print(f"  - Including directory structure: {rel_dir_path}")
        
        # Process each file
        for filename in sorted(files):  # Sort for consistency
            file_path = os.path.join(root, filename)
            # Skip files we can't read
            if not os.access(file_path, os.R_OK):
                continue
                
            # Calculate relative path for consistent hashing across systems
            rel_path = os.path.relpath(file_path, directory_path)
            
            try:
                # Hash the file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    
                content_hash = hashlib.md5(file_content).hexdigest()
                
                # Store file entry with path and hash
                file_entry = f"FILE:{rel_path}:{content_hash}"
                directory_entries.append(file_entry)
                if verbose:
                    print(f"  - Hashed file: {rel_path} -> {content_hash[:8]}...")
            except Exception as e:
                if verbose:
                    print(f"  - Error hashing file {rel_path}: {e}")
    
    # Create a combined hash from all entries
    if not directory_entries:
        return None
        
    # Sort the entries for deterministic order
    directory_entries.sort()
    
    # Combine all entries into one final hash
    combined_hash = hashlib.md5()
    for entry in directory_entries:
        combined_hash.update(entry.encode('utf-8'))
    
    final_hash = combined_hash.hexdigest()
    if verbose:
        print(f"Final directory hash: {final_hash}\n")
    return final_hash

def verify_directory_hash(directory_path, expected_hash, exclude_dirs=None, verbose=False):
    """
    Verify that a directory's current hash matches the expected hash.
    
    Args:
        directory_path (str): Path to the directory to verify
        expected_hash (str): Expected hash value
        exclude_dirs (list): List of directory names to exclude
        verbose (bool): Whether to print detailed hashing information
        
    Returns:
        bool: True if the hashes match, False otherwise
    """
    if not expected_hash:
        print(f"No expected hash provided for {directory_path}, skipping verification")
        return True
        
    current_hash = calculate_directory_hash(directory_path, exclude_dirs, verbose=verbose)
    if current_hash == expected_hash:
        print(f"Hash verification PASSED for {directory_path}")
        return True
    else:
        print(f"Hash verification FAILED for {directory_path}")
        print(f"  Expected: {expected_hash}")
        print(f"  Actual:   {current_hash}")
        #
        return False

def generate_hash_for_script(script_name):
    """
    Generate hash for a script directory.
    
    Args:
        script_name (str): Name of the script (folder name)
        
    Returns:
        str: Hash value for the script directory or None if not found
    """
    # Get the absolute path to the script folder
    script_folder = os.path.join(os.getcwd(), script_name)
    
    # Check if the directory exists
    if not os.path.isdir(script_folder):
        print(f"Error: Script folder '{script_folder}' not found")
        return None
    
    # Exclude standard directories
    exclude_dirs = ['__pycache__', '.git', '.vscode']
    
    # Generate hash
    hash_value = calculate_directory_hash(script_folder, exclude_dirs, verbose=True)
    
    if hash_value:
        print(f"\nScript: {script_name}")
        print(f"Hash: {hash_value}")
        print(f"\nAdd this to your script_hashes dictionary:")
        print(f'    "{script_name}": "{hash_value}",')
    
    return hash_value

def generate_hashes_for_directories(directories, exclude_dirs=None):
    """
    Generate hashes for a list of directories.
    
    Args:
        directories (list): List of directory paths to hash
        exclude_dirs (list): List of directory names to exclude
        
    Returns:
        dict: Dictionary mapping directory names to their hash values
    """
    hashes = {}
    
    for directory in directories:
        if os.path.isdir(directory):
            dir_name = os.path.basename(directory)
            hash_value = calculate_directory_hash(directory, exclude_dirs, verbose=True)
            hashes[dir_name] = hash_value
    
    return hashes

# Added main function to run the script directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python directory_hash.py <script_name>")
        print("This will generate a hash for the specified script directory")
        sys.exit(1)
    
    script_name = sys.argv[1]
    generate_hash_for_script(script_name)