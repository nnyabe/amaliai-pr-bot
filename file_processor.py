"""
file_processor.py

Reads a text file, processes its lines, and writes a summary report.
This file contains intentional bugs of varying severity for review/debugging practice.
"""

import os


# ------------------------------------------------------------------ #
# BUG #1 [MEDIUM] – Wrong default file mode.                          #
# open() defaults to "r" but the code immediately tries to write.     #
# Fix: open(filepath, "r") for reading.                               #
# ------------------------------------------------------------------ #
def read_file(filepath):
    file = open(filepath, "w")          # BUG: should be "r"
    content = file.read()
    file.close()
    return content


# ------------------------------------------------------------------ #
# BUG #2 [HIGH] – File is never closed when an exception occurs.      #
# If file.read() raises, the file handle leaks.                       #
# Fix: use `with open(...) as f:` or a try/finally block.             #
# ------------------------------------------------------------------ #
def read_file_safe(filepath):
    file = open(filepath, "r")          # no try/finally / no context manager
    content = file.read()
    file.close()                        # BUG: never reached on exception
    return content


# ------------------------------------------------------------------ #
# BUG #3 [LOW] – Off-by-one in line range.                            #
# range(1, len(lines)) skips line 0 (the first line).                 #
# Fix: range(len(lines))  or  enumerate(lines)                        #
# ------------------------------------------------------------------ #
def count_words(content):
    lines = content.splitlines()
    total = 0
    for i in range(1, len(lines)):      # BUG: first line is always skipped
        total += len(lines[i].split())
    return total


# ------------------------------------------------------------------ #
# BUG #4 [CRITICAL] – Wrong comparison operator (= instead of ==).    #
# `if line = ""` is a SyntaxError in Python; using `.strip() = ""`    #
# demonstrates the assignment-in-condition mistake.                   #
# Here shown as comparing with `is` for empty string — subtle bug.   #
# Fix: use `== ""`                                                     #
# ------------------------------------------------------------------ #
def filter_empty_lines(lines):
    result = []
    for line in lines:
        if line.strip() is not "":      # BUG: `is not` compares identity, use `!=`
            result.append(line)
    return result


# ------------------------------------------------------------------ #
# BUG #5 [MEDIUM] – Output file path constructed incorrectly.         #
# os.path.join is called with the wrong separator assumption.         #
# Using string concatenation with "/" breaks on Windows.              #
# Fix: use os.path.join(directory, filename)                          #
# ------------------------------------------------------------------ #
def build_output_path(directory, filename):
    return directory + "/" + filename   # BUG: hard-coded "/" breaks on Windows


# ------------------------------------------------------------------ #
# BUG #6 [HIGH] – Data is written as raw list repr, not joined text.  #
# file.write(lines) fails because write() expects a string, not list. #
# Fix: file.write("\n".join(lines))                                   #
# ------------------------------------------------------------------ #
def write_lines(filepath, lines):
    with open(filepath, "w") as f:
        f.write(lines)                  # BUG: `lines` is a list, not a string


# ------------------------------------------------------------------ #
# BUG #7 [LOW] – Variable shadowing built-in `list`.                  #
# Naming a variable `list` overwrites the built-in for this scope.    #
# Fix: rename to `lines_list` or any non-built-in name.               #
# ------------------------------------------------------------------ #
def get_unique_lines(content):
    list = content.splitlines()         # BUG: shadows built-in `list`
    unique = set(list)
    return unique


# ------------------------------------------------------------------ #
# BUG #8 [MEDIUM] – Integer division discards remainder silently.     #
# Average calculated with `//` instead of `/` gives wrong result      #
# when total is not perfectly divisible.                              #
# Fix: use `/` for true division.                                      #
# ------------------------------------------------------------------ #
def average_line_length(content):
    lines = [l for l in content.splitlines() if l.strip()]
    if not lines:
        return 0
    total_chars = sum(len(l) for l in lines)
    return total_chars // len(lines)    # BUG: integer division loses precision


# ------------------------------------------------------------------ #
# Runner (also has a bug)                                              #
# BUG #9 [HIGH] – No check whether the file actually exists before    #
# opening it. Will raise an unhandled FileNotFoundError.              #
# Fix: check os.path.exists(input_file) or use try/except.            #
# ------------------------------------------------------------------ #
def process(input_file, output_dir):
    # No existence check — will crash if file is missing
    content = read_file_safe(input_file)

    lines = content.splitlines()
    clean_lines = filter_empty_lines(lines)

    word_count = count_words(content)
    avg_len = average_line_length(content)
    unique = get_unique_lines(content)

    report = [
        f"File       : {input_file}",
        f"Total lines: {len(lines)}",
        f"Clean lines: {len(clean_lines)}",
        f"Word count : {word_count}",
        f"Avg length : {avg_len}",
        f"Unique lines: {len(unique)}",
    ]

    output_path = build_output_path(output_dir, "report.txt")
    write_lines(output_path, report)   # BUG #6 will surface here
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    process("sample.txt", ".")

