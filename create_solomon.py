"""
create_solomon.py

Creates a new file called 'solomon' safely using a context manager
and proper error handling to avoid resource leaks or unhandled exceptions.
"""

import os


def create_solomon(directory: str = ".", content: str = "") -> str:
    """
    Safely creates a file named 'solomon' in the given directory.

    Args:
        directory: The directory in which to create the file. Defaults to current directory.
        content:   Optional text content to write into the file.

    Returns:
        The absolute path of the created file.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
        OSError:           If the file cannot be created or written.
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory '{directory}' does not exist.")

    filepath = os.path.join(directory, "solomon")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"File created successfully: {os.path.abspath(filepath)}")
    except OSError as e:
        print(f"Failed to create file: {e}")
        raise

    return os.path.abspath(filepath)


if __name__ == "__main__":
    create_solomon(
        directory=".",
        content="Hello, I am Solomon.\n",
    )

