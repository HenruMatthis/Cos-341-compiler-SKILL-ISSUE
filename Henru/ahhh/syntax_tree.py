# syntax_tree.py
import json

class ASTNode:
    """
    Represents a node in the Abstract Syntax Tree (AST).
    Each node has a name (grammar symbol), optional value, and a list of child nodes.
    """
    def __init__(self, name, children=None, value=None):
        self.name = name
        self.children = children or []
        self.value = value

    def __repr__(self):
        """Default flat representation (used when printing from parser)."""
        return f"{self.name}({self.value if self.value else ''})"

    def pretty_print(self, prefix: str = "", is_last: bool = True):
        """
        Recursively draw the syntax tree with connecting lines.
        Example:
        SPL_PROG
        ├── VARIABLES
        │   ├── VAR: x
        │   └── VAR: y
        └── MAINPROG
            └── PRINT: c
        """
        connector = "└── " if is_last else "├── "
        line = f"{prefix}{connector}{self.name}"
        if self.value:
            line += f": {self.value}"
        print(line)

        # Update prefix for children
        new_prefix = prefix + ("    " if is_last else "│   ")

        # Print children recursively
        for i, child in enumerate(self.children):
            is_last_child = i == len(self.children) - 1
            child.pretty_print(new_prefix, is_last_child)

    def to_dict(self):
        """Convert the AST into a nested dictionary (useful for JSON export)."""
        return {
            "name": self.name,
            "value": self.value,
            "children": [child.to_dict() for child in self.children]
        }

    def to_json(self, indent=2):
        """Return the JSON representation of the AST."""
        return json.dumps(self.to_dict(), indent=indent)


# Example tree test
if __name__ == "__main__":
    tree = ASTNode("SPL_PROG", [
        ASTNode("VARIABLES", [
            ASTNode("VAR", value="x"),
            ASTNode("VAR", value="y")
        ]),
        ASTNode("PROCDEFS", [
            ASTNode("PDEF", [
                ASTNode("PARAM", value="a"),
                ASTNode("BODY", [
                    ASTNode("INSTR", value="halt")
                ])
            ], value="test")
        ]),
        ASTNode("FUNCDEFS", [
            ASTNode("FDEF", [
                ASTNode("PARAM", value="a"),
                ASTNode("BODY", [
                    ASTNode("INSTR", value="halt")
                ]),
                ASTNode("ATOM", value="a")
            ], value="fun")
        ]),
        ASTNode("MAINPROG", [
            ASTNode("VARIABLES", [ASTNode("VAR", value="c")]),
            ASTNode("ALGO", [ASTNode("PRINT", [ASTNode("ATOM", value="c")])])
        ])
    ])

    print(" Syntax Tree Visualization:")
    tree.pretty_print()
