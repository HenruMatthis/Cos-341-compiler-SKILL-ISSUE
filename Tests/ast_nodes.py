# ast_nodes.py
# Defines the node structures for the Abstract Syntax Tree (AST)

# Import 'fields' (plural) to iterate over dataclass fields
from dataclasses import dataclass, field, fields
from typing import List, Optional, Union

# --- Base Node ---
@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    
    def pretty_print(self, indent_level: int = 0) -> str:
        """Recursively builds an indented string representation of the node."""
        indent = "  " * indent_level
        node_name = self.__class__.__name__
        
        parts = [f"{indent}{node_name}:"]
        
        # *** FIX: Use fields() (plural) to iterate ***
        for f in fields(self):
            val = getattr(self, f.name)
            child_indent = "  " * (indent_level + 1)
            
            if isinstance(val, ASTNode):
                # Add field name before node
                parts.append(f"{child_indent}{f.name}:")
                parts.append(val.pretty_print(indent_level + 2)) # Indent child node
            elif isinstance(val, list):
                if all(isinstance(item, ASTNode) for item in val):
                    parts.append(f"{child_indent}{f.name}: [")
                    for item in val:
                        parts.append(item.pretty_print(indent_level + 2))
                    parts.append(f"{child_indent}]")
                elif val: # Only print non-empty primitive lists
                    parts.append(f"{child_indent}{f.name}: {val!r}")
            elif val is not None:
                parts.append(f"{child_indent}{f.name}: {val!r}")
                
        return "\n".join(parts)

# --- Forward Declarations for Type Hinting ---
# (Removed as they are not strictly necessary with string hints or
#  the current class structure, but can be added back if needed)

# --- Specific Node Classes ---
# Overriding pretty_print for simple/leaf nodes

@dataclass
class ProgramNode(ASTNode):
    globals: 'VariableDeclsNode'
    procs: 'ProcDefsNode'
    funcs: 'FuncDefsNode'
    main: 'MainProgNode'

@dataclass
class VarNode(ASTNode):
    name: str
    def pretty_print(self, indent_level: int = 0) -> str:
        return f"{'  ' * indent_level}VarNode(name={self.name!r})"

@dataclass
class VariableDeclsNode(ASTNode):
    variables: List[VarNode] = field(default_factory=list)

@dataclass
class ProcedureDefNode(ASTNode):
    name: VarNode
    params: 'Max3Node'
    body: 'BodyNode'

@dataclass
class ProcDefsNode(ASTNode):
    procedures: List[ProcedureDefNode] = field(default_factory=list)

@dataclass
class FunctionDefNode(ASTNode):
    name: VarNode
    params: 'Max3Node'
    body: 'BodyNode'
    return_atom: 'AtomNode'

@dataclass
class FuncDefsNode(ASTNode):
    functions: List[FunctionDefNode] = field(default_factory=list)

@dataclass
class BodyNode(ASTNode):
    locals: 'Max3Node'
    algorithm: 'AlgorithmNode'

@dataclass
class Max3Node(ASTNode):
    variables: List[VarNode] = field(default_factory=list)

@dataclass
class MainProgNode(ASTNode):
    locals: 'VariableDeclsNode'
    algorithm: 'AlgorithmNode'

@dataclass
class AtomNode(ASTNode):
    value: Union[VarNode, int]
    def pretty_print(self, indent_level: int = 0) -> str:
        indent = "  " * indent_level
        if isinstance(self.value, VarNode):
            # Print VarNode inline for AtomNode
            return f"{indent}AtomNode(value={self.value.pretty_print(0)})"
        else:
            return f"{indent}AtomNode(value={self.value!r})"

@dataclass
class AlgorithmNode(ASTNode):
    instructions: List[ASTNode] = field(default_factory=list)

# --- Instruction Nodes ---

@dataclass
class HaltNode(ASTNode):
    def pretty_print(self, indent_level: int = 0) -> str:
        return f"{'  ' * indent_level}HaltNode"

@dataclass
class PrintNode(ASTNode):
    output: Union[AtomNode, str]
    def pretty_print(self, indent_level: int = 0) -> str:
        indent = "  " * indent_level
        if isinstance(self.output, ASTNode):
            # Print node content inline or nested
            return f"{indent}PrintNode(\n{indent}  output:\n{self.output.pretty_print(indent_level + 2)}\n{indent})"
        else:
            # For string literals
            return f"{indent}PrintNode(output={self.output!r})"

@dataclass
class ProcedureCallNode(ASTNode):
    name: VarNode
    arguments: 'InputNode'

@dataclass
class AssignmentNode(ASTNode):
    variable: VarNode
    rhs: ASTNode 

@dataclass
class FunctionCallNode(ASTNode):
    name: VarNode
    arguments: 'InputNode'

@dataclass
class WhileLoopNode(ASTNode):
    condition: 'TermNode'
    body: 'AlgorithmNode'

@dataclass
class DoUntilLoopNode(ASTNode):
    body: 'AlgorithmNode'
    condition: 'TermNode'

@dataclass
class IfBranchNode(ASTNode):
    condition: 'TermNode'
    then_branch: 'AlgorithmNode'
    else_branch: Optional['AlgorithmNode'] = None

# --- Expression/Term Nodes ---

@dataclass
class UnaryOperationNode(ASTNode):
    operator: str
    operand: 'TermNode'
    def pretty_print(self, indent_level: int = 0) -> str:
        indent = "  " * indent_level
        return (f"{indent}UnaryOperationNode(operator={self.operator!r},\n"
                f"{'  ' * (indent_level + 1)}operand:\n{self.operand.pretty_print(indent_level + 2)}\n{indent})")

@dataclass
class BinaryOperationNode(ASTNode):
    left_operand: 'TermNode'
    operator: str
    right_operand: 'TermNode'
    def pretty_print(self, indent_level: int = 0) -> str:
        indent = "  " * indent_level
        return (f"{indent}BinaryOperationNode(operator={self.operator!r},\n"
                f"{'  ' * (indent_level + 1)}left_operand:\n{self.left_operand.pretty_print(indent_level + 2)},\n"
                f"{'  ' * (indent_level + 1)}right_operand:\n{self.right_operand.pretty_print(indent_level + 2)}\n{indent})")

@dataclass
class ParenTermNode(ASTNode):
    term: Union[UnaryOperationNode, BinaryOperationNode]
    def pretty_print(self, indent_level: int = 0) -> str:
        # Print the wrapped term directly
        return self.term.pretty_print(indent_level)

@dataclass
class TermNode(ASTNode):
    value: Union[AtomNode, ParenTermNode]
    def pretty_print(self, indent_level: int = 0) -> str:
        # Print the wrapped value directly
        return self.value.pretty_print(indent_level)

# --- Input/Output Nodes ---
@dataclass
class OutputNode(ASTNode): # Unused by parser, but defined
     value: Union[AtomNode, str]

@dataclass
class InputNode(ASTNode):
    arguments: List[AtomNode] = field(default_factory=list)