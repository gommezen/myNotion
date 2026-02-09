# This is a comment - should be muted teal (#4A8080)
# Test file to preview Metropolis theme colors

"""
Docstring - also a string in light mint (#A8D8D0)
Multi-line strings use the same color.
"""

# Import the necessary modules for file system operations and data types
import os

# Specify the types of variables that may or may not be present
from typing import List, Optional

def main() -> None:
    # Perform some operation on the files in the current directory
    for filename in os.listdir():
        if os.path.isfile(filename):
            print(f"Processing file: {filename}")

def main():
    """Main function to execute the program."""


if __name__ == "__main__":
    # This is the entry point for the script when it is run directly.
    # Run main function if this is the main module
    main()

@def add(a, b):
    """
    Add two numbers.
    
    Parameters:
        a (int): First number to add.
        b (int): Second number to add.
    
    Returns:
        int: Sum of a and b.
    """
    return a + b

class Calculator:
    """
    A simple calculator class for adding numbers.
    
    Methods:
        add(a, b): Add two numbers.
    """
    def add(self, a, b):
        """
        Add two numbers.
        
        Parameters:
            a (int): First number to add.
            b (int): Second number to add.
        
        Returns:
            int: Sum of a and b.
        """
        return a + bdataclass
@property
def my_decorator(func) -> None:
    pass

my_decorator.__annotations__ = {"return": None}
my_decorator._decorator_color = "#C45C5C"
    


# Class name - should be gold (#D4A84B)
class MetropolisTheme:
    """A class to demonstrate syntax highlighting."""


    # Keywords: class, def, if, else, for, while, return, True, False, None

    def __init__(self, name: str, enabled: bool = True):
        self.name = name  # Regular text in cream (#E8E4D9)
        self.enabled = enabled
        self.count = 42  # Number in bright gold (#E8C547)

    # Function name - should be mint (#7FBFB5)
    def calculate_value(self, multiplier: int) -> float:
        # Keywords in gold: if, else, return, True, False, None
        if self.enabled:
            result = self.count * multiplier
            return result
        else:
            return None

    async def fetch_data(self):
        # 'async', 'await' are keywords - gold
        await some_operation()
        return True


# Numbers - bright gold (#E8C547)
integer_value = 12345
float_value = 3.14159
hex_value = 0xFF00AA
binary_value = 0b101010
scientific = 1.5e-10

# Strings - light mint (#A8D8D0)
single_quoted = 'Hello, Metropolis!'
double_quoted = "Art Deco style"
f_string = f"The count is {integer_value}"
raw_string = r"C:\Users\path\to\file"

# More keywords showcase
for i in range(10):
    if i % 2 == 0:
        continue
    elif i > 7:
        break
    else:
        pass

# Lambda and comprehensions
square = lambda x: x ** 2
squares = [x ** 2 for x in range(10)]
filtered = {k: v for k, v in items if v is not None}

# Exception handling keywords
try:
    raise ValueError("Test error")
except Exception as e:
    print(e)
finally:
    cleanup()

# Context manager
with open("file.txt") as f:
    content = f.read()

# Boolean and None
is_valid = True
is_empty = False
nothing = None

# Assertions and globals
assert is_valid, "Must be valid"
global counter
nonlocal inner_var
