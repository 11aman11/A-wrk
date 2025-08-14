def C(filename):
    print(f"Opening file: {filename}")
    with open(filename, 'r') as f:  # This will fail if file doesn't exist
        data = f.read()
    return data