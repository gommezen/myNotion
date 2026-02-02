# This is a comment - should be muted teal (#4A8080)
# Test file to preview Metropolis theme colors

"""
Docstring - also a string in light mint (#A8D8D0)
Multi-line strings use the same color.
"""

import os  # keyword 'import' in gold (#D4A84B)
from typing import List, Optional  # keywords in gold


# Decorator - should be red accent (#C45C5C)
@dataclass
@property
def my_decorator(func):
    pass


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
