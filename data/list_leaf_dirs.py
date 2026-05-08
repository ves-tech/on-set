import yaml
import os
import sys

def print_leaf_paths(node, parent_path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            current_path = os.path.join(parent_path, key) if parent_path else key
            if value is None or (isinstance(value, list) and len(value) == 0) or (isinstance(value, dict) and len(value) == 0):
                print(current_path)
            else:
                print_leaf_paths(value, current_path)
    elif isinstance(node, list):
        if not node:
            if parent_path:
                print(parent_path)
        else:
            for item in node:
                print_leaf_paths(item, parent_path)
    elif isinstance(node, str):
        current_path = os.path.join(parent_path, node) if parent_path else node
        print(current_path)
    else:
        # Handle cases like numbers or booleans if they ever appear
        pass

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_file = os.path.join(script_dir, "directory_structure.yaml")
    
    try:
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)
            
        print_leaf_paths(data)
    except Exception as e:
        print(f"Error reading or parsing YAML file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
