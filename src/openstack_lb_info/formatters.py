# -*- coding: utf-8 -*-
"""
Output Formatters Module
------------------------

This module provides classes for formatting and displaying output in different formats,
including Rich text, plain text, and JSON. It defines an abstract base class `OutputFormatter`
and concrete implementations for each output format. These formatters are used to present
information about OpenStack resources in a user-friendly and structured manner.
"""

import contextlib
import json
import re
from abc import ABC, abstractmethod

try:
    from rich.console import Console
    from rich.highlighter import ReprHighlighter
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def create_tree(self, name):
        """Create a tree structure for the output."""

    @abstractmethod
    def add_to_tree(self, tree, content):
        """Add content to the tree structure."""

    @abstractmethod
    def print_tree(self, tree):
        """Print the tree structure."""

    @abstractmethod
    def print(self, message):
        """Print a message."""

    @abstractmethod
    def status(self, message):
        """Display a status message."""

    @abstractmethod
    def line(self):
        """Print a line separator."""

    @abstractmethod
    def rule(self, title, align="center"):
        """Print a rule with a title."""

    @abstractmethod
    def format_status(self, status):
        """Format status text."""


class RichOutputFormatter(OutputFormatter):
    """Formatter using the Rich library."""

    def __init__(self):
        self.console = Console()
        self.highlighter = ReprHighlighter()

    def create_tree(self, name):
        return Tree(name)

    def add_to_tree(self, tree, content, highlight=False):
        if highlight:
            content = self.highlighter(content)
        return tree.add(content)

    def print_tree(self, tree):
        self.console.print(tree)

    def print(self, message):
        self.console.print(message)

    def status(self, message):
        return self.console.status(message)

    def line(self):
        self.console.line()

    def rule(self, title, align="center"):
        self.console.rule(title, align=align)

    def format_message(self, message):
        """Return the message as-is, preserving Rich formatting."""
        return message

    def format_status(self, status):
        status_colors = {
            "ACTIVE": "green",
            "ONLINE": "green",
            "PENDING": "yellow",
        }
        color = status_colors.get(status, "red")
        return f"[{color}]{status}[/{color}]"


class PlainOutputFormatter(OutputFormatter):
    """Formatter for plain text output."""

    def create_tree(self, name):
        return {"name": name, "children": []}

    def add_to_tree(self, tree, content, highlight=False):
        _ = highlight
        child_tree = {"name": self.format_message(content), "children": []}
        tree["children"].append(child_tree)
        return child_tree

    def print_tree(self, tree, level=0):
        indent = "    " * level
        print(f"{indent}{self.format_message(tree['name'])}")
        for child in tree.get("children", []):
            self.print_tree(child, level + 1)

    def print(self, message):
        print(self.format_message(message))

    def status(self, message):
        @contextlib.contextmanager
        def plain_status():
            # Remove Rich formatting codes from the message
            clean_message = self.format_message(message)
            print(f"[STATUS] {clean_message}")
            try:
                yield
            finally:
                print(f"[STATUS] Completed: {clean_message}")

        return plain_status()

    def line(self):
        print()

    def rule(self, title, align="center"):
        title = self.format_message(title)
        print(f"{title}")
        print("-" * len(title))

    def format_message(self, message):
        """Remove Rich text formatting tags from a message."""
        clean_message = re.sub(r"\[\/?[^\]]+\]", "", message)
        return clean_message

    def format_status(self, status):
        return status


class JSONOutputFormatter(OutputFormatter):
    """Formatter for JSON output."""

    def __init__(self):
        self.data = None

    def create_tree(self, name):
        # Remove Rich codes
        clean_name = self.format_message(name)
        self.data = {"name": clean_name, "children": []}
        return self.data

    def add_to_tree(self, tree, content, highlight=False):
        _ = highlight
        # Remove Rich codes
        clean_content = self.format_message(content)
        # Create a new node and add it to the tree's children
        child = {"name": clean_content, "children": []}
        tree["children"].append(child)
        return child

    def print_tree(self, tree):
        print(json.dumps(tree, indent=4))

    def print(self, message):
        # Remove Rich codes
        clean_message = self.format_message(message)
        # Not show empty prints
        if not clean_message:
            return
        # For consistency, wrap messages in a dict
        output = {"message": clean_message}
        print(json.dumps(output, indent=4))

    def status(self, message):
        return contextlib.nullcontext()

    def line(self):
        pass

    def rule(self, title, align="center"):
        pass

    def format_status(self, status):
        return status

    def format_message(self, message):
        """Remove Rich text formatting tags from a message."""
        if isinstance(message, str):
            clean_message = re.sub(r"\[\/?[^\]]+\]", "", message)
            return clean_message
        return message


# vim: ts=4
