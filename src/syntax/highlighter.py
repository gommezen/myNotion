"""
Syntax highlighting using QSyntaxHighlighter.
Supports Python, JavaScript, HTML, CSS, and plain text.
"""

from enum import Enum, auto
from typing import TYPE_CHECKING, NamedTuple, Optional

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextDocument

if TYPE_CHECKING:
    from core.settings import EditorTheme


class HighlightRule(NamedTuple):
    """A pattern and format pair for syntax highlighting."""

    pattern: QRegularExpression
    format: QTextCharFormat


class Language(Enum):
    """Supported languages for syntax highlighting."""

    PLAIN = auto()
    PYTHON = auto()
    JAVASCRIPT = auto()
    HTML = auto()
    CSS = auto()
    JSON = auto()
    MARKDOWN = auto()


# File extension to language mapping
EXTENSION_MAP = {
    ".py": Language.PYTHON,
    ".pyw": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.JAVASCRIPT,
    ".tsx": Language.JAVASCRIPT,
    ".html": Language.HTML,
    ".htm": Language.HTML,
    ".xml": Language.HTML,
    ".css": Language.CSS,
    ".scss": Language.CSS,
    ".json": Language.JSON,
    ".md": Language.MARKDOWN,
    ".markdown": Language.MARKDOWN,
    ".txt": Language.PLAIN,
}


def get_language_from_extension(filepath: str) -> Language:
    """Determine language from file extension."""
    if not filepath:
        return Language.PLAIN

    filepath_lower = filepath.lower()
    for ext, lang in EXTENSION_MAP.items():
        if filepath_lower.endswith(ext):
            return lang
    return Language.PLAIN


class BaseHighlighter(QSyntaxHighlighter):
    """Base syntax highlighter with common functionality."""

    # Default colors (Dark theme)
    DEFAULT_COLORS = {
        "keyword": "#569CD6",
        "string": "#CE9178",
        "comment": "#6A9955",
        "number": "#B5CEA8",
        "function": "#DCDCAA",
        "class_name": "#4EC9B0",
        "decorator": "#C586C0",
    }

    def __init__(self, document: QTextDocument, theme: Optional["EditorTheme"] = None):
        super().__init__(document)
        self.theme = theme
        self.rules: list[HighlightRule] = []
        self._setup_formats()
        self._setup_rules()

    def _get_color(self, key: str) -> str:
        """Get color from theme or use default."""
        if self.theme:
            return getattr(self.theme, key, self.DEFAULT_COLORS.get(key, "#FFFFFF"))
        return self.DEFAULT_COLORS.get(key, "#FFFFFF")

    def _setup_formats(self):
        """Create text formats for different syntax elements."""
        # Keywords - use numeric weight to avoid font size issues
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(self._get_color("keyword")))
        self.keyword_format.setFontWeight(700)  # Bold weight as integer

        # Strings
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(self._get_color("string")))

        # Comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(self._get_color("comment")))
        self.comment_format.setFontItalic(True)

        # Numbers
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(self._get_color("number")))

        # Functions/methods
        self.function_format = QTextCharFormat()
        self.function_format.setForeground(QColor(self._get_color("function")))

        # Classes/types
        self.class_format = QTextCharFormat()
        self.class_format.setForeground(QColor(self._get_color("class_name")))

        # Operators
        self.operator_format = QTextCharFormat()
        foreground = self._get_color("foreground") if self.theme else "#D4D4D4"
        self.operator_format.setForeground(QColor(foreground))

        # Decorators/attributes
        self.decorator_format = QTextCharFormat()
        self.decorator_format.setForeground(QColor(self._get_color("decorator")))

    def _setup_rules(self):
        """Override in subclasses to define highlighting rules."""
        pass

    def highlightBlock(self, text: str):
        """Apply highlighting rules to a block of text."""
        for rule in self.rules:
            match_iterator = rule.pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), rule.format)


class PythonHighlighter(BaseHighlighter):
    """Syntax highlighter for Python code."""

    def _setup_rules(self):
        """Define Python syntax highlighting rules."""
        # Keywords
        keywords = [
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "False",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "True",
            "try",
            "while",
            "with",
            "yield",
            "match",
            "case",
            "type",
        ]
        keyword_pattern = r"\b(" + "|".join(keywords) + r")\b"
        self.rules.append(HighlightRule(QRegularExpression(keyword_pattern), self.keyword_format))

        # Built-in functions
        builtins = [
            "abs",
            "all",
            "any",
            "bin",
            "bool",
            "bytes",
            "callable",
            "chr",
            "classmethod",
            "compile",
            "complex",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "eval",
            "exec",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "globals",
            "hasattr",
            "hash",
            "help",
            "hex",
            "id",
            "input",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "locals",
            "map",
            "max",
            "memoryview",
            "min",
            "next",
            "object",
            "oct",
            "open",
            "ord",
            "pow",
            "print",
            "property",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "setattr",
            "slice",
            "sorted",
            "staticmethod",
            "str",
            "sum",
            "super",
            "tuple",
            "type",
            "vars",
            "zip",
        ]
        builtin_pattern = r"\b(" + "|".join(builtins) + r")\b"
        self.rules.append(HighlightRule(QRegularExpression(builtin_pattern), self.function_format))

        # Decorators
        self.rules.append(HighlightRule(QRegularExpression(r"@\w+"), self.decorator_format))

        # Class definitions
        self.rules.append(HighlightRule(QRegularExpression(r"\bclass\s+(\w+)"), self.class_format))

        # Function definitions
        self.rules.append(HighlightRule(QRegularExpression(r"\bdef\s+(\w+)"), self.function_format))

        # Numbers
        self.rules.append(
            HighlightRule(
                QRegularExpression(r"\b[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b"), self.number_format
            )
        )

        # Single-line strings
        self.rules.append(
            HighlightRule(QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.string_format)
        )
        self.rules.append(
            HighlightRule(QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), self.string_format)
        )

        # f-strings (basic support)
        self.rules.append(
            HighlightRule(QRegularExpression(r'f"[^"\\]*(\\.[^"\\]*)*"'), self.string_format)
        )
        self.rules.append(
            HighlightRule(QRegularExpression(r"f'[^'\\]*(\\.[^'\\]*)*'"), self.string_format)
        )

        # Comments
        self.rules.append(HighlightRule(QRegularExpression(r"#[^\n]*"), self.comment_format))

        # self keyword
        self.rules.append(HighlightRule(QRegularExpression(r"\bself\b"), self.decorator_format))


class JavaScriptHighlighter(BaseHighlighter):
    """Syntax highlighter for JavaScript/TypeScript code."""

    def _setup_rules(self):
        """Define JavaScript syntax highlighting rules."""
        # Keywords
        keywords = [
            "async",
            "await",
            "break",
            "case",
            "catch",
            "class",
            "const",
            "continue",
            "debugger",
            "default",
            "delete",
            "do",
            "else",
            "export",
            "extends",
            "false",
            "finally",
            "for",
            "function",
            "if",
            "import",
            "in",
            "instanceof",
            "let",
            "new",
            "null",
            "return",
            "static",
            "super",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "undefined",
            "var",
            "void",
            "while",
            "with",
            "yield",
            "interface",
            "type",
            "enum",
            "implements",
            "private",
            "protected",
            "public",
            "readonly",
        ]
        keyword_pattern = r"\b(" + "|".join(keywords) + r")\b"
        self.rules.append(HighlightRule(QRegularExpression(keyword_pattern), self.keyword_format))

        # Built-in objects
        builtins = [
            "Array",
            "Boolean",
            "Date",
            "Error",
            "Function",
            "JSON",
            "Math",
            "Number",
            "Object",
            "Promise",
            "RegExp",
            "String",
            "console",
            "window",
            "document",
            "Map",
            "Set",
            "Symbol",
        ]
        builtin_pattern = r"\b(" + "|".join(builtins) + r")\b"
        self.rules.append(HighlightRule(QRegularExpression(builtin_pattern), self.class_format))

        # Function calls
        self.rules.append(HighlightRule(QRegularExpression(r"\b\w+(?=\()"), self.function_format))

        # Numbers
        self.rules.append(
            HighlightRule(
                QRegularExpression(r"\b[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b"), self.number_format
            )
        )

        # Strings
        self.rules.append(
            HighlightRule(QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.string_format)
        )
        self.rules.append(
            HighlightRule(QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), self.string_format)
        )
        self.rules.append(
            HighlightRule(QRegularExpression(r"`[^`\\]*(\\.[^`\\]*)*`"), self.string_format)
        )

        # Single-line comments
        self.rules.append(HighlightRule(QRegularExpression(r"//[^\n]*"), self.comment_format))


class HTMLHighlighter(BaseHighlighter):
    """Syntax highlighter for HTML/XML code."""

    def _setup_rules(self):
        """Define HTML syntax highlighting rules."""
        # Tags
        self.rules.append(
            HighlightRule(QRegularExpression(r"</?[a-zA-Z][a-zA-Z0-9]*"), self.keyword_format)
        )
        self.rules.append(HighlightRule(QRegularExpression(r"/?>"), self.keyword_format))

        # Attributes
        self.rules.append(
            HighlightRule(QRegularExpression(r"\b[a-zA-Z-]+(?==)"), self.function_format)
        )

        # Attribute values
        self.rules.append(HighlightRule(QRegularExpression(r'"[^"]*"'), self.string_format))
        self.rules.append(HighlightRule(QRegularExpression(r"'[^']*'"), self.string_format))

        # Comments
        self.rules.append(HighlightRule(QRegularExpression(r"<!--.*-->"), self.comment_format))


class CSSHighlighter(BaseHighlighter):
    """Syntax highlighter for CSS code."""

    def _setup_rules(self):
        """Define CSS syntax highlighting rules."""
        # Selectors (class, id, element)
        self.rules.append(
            HighlightRule(
                QRegularExpression(r"[.#]?[a-zA-Z][a-zA-Z0-9_-]*(?=\s*\{)"), self.keyword_format
            )
        )

        # Properties
        self.rules.append(
            HighlightRule(QRegularExpression(r"[a-zA-Z-]+(?=\s*:)"), self.function_format)
        )

        # Values
        self.rules.append(HighlightRule(QRegularExpression(r":\s*[^;{}]+"), self.string_format))

        # Numbers with units
        self.rules.append(
            HighlightRule(
                QRegularExpression(r"\b[0-9]+\.?[0-9]*(px|em|rem|%|vh|vw|deg|s|ms)?\b"),
                self.number_format,
            )
        )

        # Colors
        self.rules.append(
            HighlightRule(QRegularExpression(r"#[0-9a-fA-F]{3,8}\b"), self.number_format)
        )

        # Comments
        self.rules.append(HighlightRule(QRegularExpression(r"/\*.*\*/"), self.comment_format))


class JSONHighlighter(BaseHighlighter):
    """Syntax highlighter for JSON code."""

    def _setup_rules(self):
        """Define JSON syntax highlighting rules."""
        # Keys
        self.rules.append(
            HighlightRule(QRegularExpression(r'"[^"]*"(?=\s*:)'), self.function_format)
        )

        # String values
        self.rules.append(HighlightRule(QRegularExpression(r':\s*"[^"]*"'), self.string_format))

        # Numbers
        self.rules.append(
            HighlightRule(
                QRegularExpression(r"\b-?[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b"), self.number_format
            )
        )

        # Booleans and null
        self.rules.append(
            HighlightRule(QRegularExpression(r"\b(true|false|null)\b"), self.keyword_format)
        )


class MarkdownHighlighter(BaseHighlighter):
    """Syntax highlighter for Markdown code."""

    def _setup_rules(self):
        """Define Markdown syntax highlighting rules."""
        # Headers
        self.rules.append(HighlightRule(QRegularExpression(r"^#{1,6}\s.*$"), self.keyword_format))

        # Bold
        self.rules.append(HighlightRule(QRegularExpression(r"\*\*[^*]+\*\*"), self.function_format))
        self.rules.append(HighlightRule(QRegularExpression(r"__[^_]+__"), self.function_format))

        # Italic
        self.rules.append(HighlightRule(QRegularExpression(r"\*[^*]+\*"), self.decorator_format))
        self.rules.append(HighlightRule(QRegularExpression(r"_[^_]+_"), self.decorator_format))

        # Code
        self.rules.append(HighlightRule(QRegularExpression(r"`[^`]+`"), self.string_format))

        # Links
        self.rules.append(
            HighlightRule(QRegularExpression(r"\[([^\]]+)\]\([^)]+\)"), self.class_format)
        )

        # Lists
        self.rules.append(HighlightRule(QRegularExpression(r"^\s*[-*+]\s"), self.number_format))
        self.rules.append(HighlightRule(QRegularExpression(r"^\s*\d+\.\s"), self.number_format))


def create_highlighter(
    language: Language, document: QTextDocument, theme: Optional["EditorTheme"] = None
) -> BaseHighlighter:
    """Factory function to create the appropriate highlighter."""
    highlighters = {
        Language.PYTHON: PythonHighlighter,
        Language.JAVASCRIPT: JavaScriptHighlighter,
        Language.HTML: HTMLHighlighter,
        Language.CSS: CSSHighlighter,
        Language.JSON: JSONHighlighter,
        Language.MARKDOWN: MarkdownHighlighter,
        Language.PLAIN: BaseHighlighter,
    }
    highlighter_class = highlighters.get(language, BaseHighlighter)
    return highlighter_class(document, theme)
