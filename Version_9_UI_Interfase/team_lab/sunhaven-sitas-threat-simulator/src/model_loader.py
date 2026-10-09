import json


def load_environment(file_path):
    """
    Load the fictional Sunhaven environment from a JSON file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if "nodes" not in data:
            raise ValueError("Environment file is missing 'nodes'.")

        if "relationships" not in data:
            raise ValueError("Environment file is missing 'relationships'.")

        return data

    except FileNotFoundError:
        print(f"Error: file not found: {file_path}")
        return None

    except json.JSONDecodeError:
        print(f"Error: invalid JSON in: {file_path}")
        return None

    except ValueError as error:
        print(f"Error: {error}")
        return None

def load_json_file(file_path):
    """
    Load a general JSON configuration file.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        print(f"Error: file not found: {file_path}")
        return None

    except json.JSONDecodeError:
        print(f"Error: invalid JSON in: {file_path}")
        return None    
