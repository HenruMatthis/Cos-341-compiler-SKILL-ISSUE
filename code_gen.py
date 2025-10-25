# code_gen.py
"""
Generates Intermediate Representation (IR) code (similar to Three-Address Code)
from the validated and annotated SPL Abstract Syntax Tree (AST).
Implements Task 7 based on Phase 4 specifications and Chapter 6 concepts.
"""

from typing import List, Optional, Union, Dict, Any
from ast_nodes import *
from symbol_table import SymbolTable, SymbolInfo, SymbolTableError
from semantic_analyzer import SemanticAnalyzer # To get type info

class CodeGenError(Exception):
    pass

class CodeGenerator:
    def __init__(self, symbol_table: SymbolTable, node_types: Dict[int, str]):
        self.symbol_table = symbol_table
        self.node_types = node_types # Type info from semantic analyzer
        self.ir_code: List[str] = []
        self._temp_counter = 0
        self._label_counter = 0
        self._current_scope_node_id = 0 # To help lookup symbols

    def _new_temp(self) -> str:
        """Generates a new unique temporary variable name."""
        self._temp_counter += 1
        return f"t{self._temp_counter}" # [cite: 1974]

    def _new_label(self) -> str:
        """Generates a new unique label name."""
        self._label_counter += 1
        return f"L{self._label_counter}" # [cite: 2074]

    def _emit(self, instruction: str):
        """Adds an instruction to the IR code list."""
        self.ir_code.append(instruction)

    def _get_unique_var_name(self, var_name: str, node: ASTNode) -> str:
        """Looks up the unique IR name for a variable."""
        # We need the correct scope context for lookup, which isn't directly
        # available here. A robust implementation would pass scope info down
        # or have the symbol table track current scope during traversal.
        # For now, we'll assume a simpler lookup based on name,
        # relying on the semantic analysis having passed.
        # A better approach involves linking AST nodes directly to SymbolInfo
        # during semantic analysis or passing scope info.
        info = self.symbol_table.lookup(var_name) # Simplistic lookup
        if not info:
            raise CodeGenError(f"CodeGen: Variable '{var_name}' not found in symbol table (should not happen after semantic analysis)")
        return info.unique_name

    def generate(self, ast: ProgramNode) -> List[str]:
        """Main entry point to generate IR code for the entire program."""
        self.ir_code = []
        self._temp_counter = 0
        self._label_counter = 0

        # SPL starts execution in 'main'
        self._visit(ast.main)

        return self.ir_code

    # --- Visitor Methods ---
    def _visit(self, node: Optional[ASTNode]) -> Optional[str]:
        """Generic dispatch method."""
        if node is None:
            return None
        method_name = f'_visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node: ASTNode):
        """Fallback for unhandled node types."""
        raise CodeGenError(f"No visitor method for node type: {type(node).__name__}")

    def _visit_MainProgNode(self, node: MainProgNode):
        # Global variable declarations are handled by symbol table, no code gen needed [cite: 2675-2677]
        # Local variable declarations for main are also just for symbol table [cite: 2675-2677]
        self._visit(node.algorithm)

    def _visit_AlgorithmNode(self, node: AlgorithmNode):
        for instr in node.instructions:
            self._visit(instr) # Generate code sequentially 

    def _visit_HaltNode(self, node: HaltNode):
        self._emit("STOP") # 

    def _visit_PrintNode(self, node: PrintNode):
        if isinstance(node.output, str):
            # String literal needs quotes in IR/BASIC 
            self._emit(f'PRINT "{node.output}"')
        elif isinstance(node.output, AtomNode):
            atom_place = self._visit(node.output)
            self._emit(f"PRINT {atom_place}") # 
        else:
            raise CodeGenError("Invalid PrintNode output")

    def _visit_AssignmentNode(self, node: AssignmentNode):
        rhs_place = self._visit(node.rhs) # Evaluate RHS into a temp or use directly
        lhs_var_unique_name = self._visit(node.variable)
        self._emit(f"{lhs_var_unique_name} = {rhs_place}") # 

    def _visit_AtomNode(self, node: AtomNode) -> str:
        """Returns the place (variable name or constant) containing the atom's value."""
        if isinstance(node.value, VarNode):
            # Return the unique IR name for the variable 
            return self._visit(node.value)
        elif isinstance(node.value, int):
            # For constants, we might assign to a temp or use directly
            # Let's assign to a temp for consistency with Chapter 6 style 
            temp = self._new_temp()
            self._emit(f"{temp} = {node.value}")
            return temp
        else:
            raise CodeGenError(f"Unknown AtomNode value type: {type(node.value)}")

    def _visit_TermNode(self, node: TermNode) -> str:
        """Visit a term, returning the place holding its value."""
        return self._visit(node.value) # Delegate to Atom or ParenTerm

    def _visit_ParenTermNode(self, node: ParenTermNode) -> str:
        """Visit parenthesized term, returning the place holding its value."""
        # The parens primarily affect parsing; codegen visits the inner expression
        return self._visit(node.term) # Delegate to UnaryOp or BinaryOp [cite: 2710-2711]

    def _visit_UnaryOperationNode(self, node: UnaryOperationNode) -> str:
        operand_place = self._visit(node.operand)
        result_place = self._new_temp()
        op_symbol = ""
        if node.operator == 'neg':
            op_symbol = "-" # 
            self._emit(f"{result_place} = {op_symbol} {operand_place}")
        elif node.operator == 'not':
            # 'not' is handled during conditional jumps, not as a direct calculation [cite: 2719-2720]
            # This node should primarily appear within a condition context
            # If used directly (e.g., x = (not y)), we'd need a way to represent boolean values,
            # which SPL doesn't explicitly support outside conditions.
            # We'll assume 'not' only affects control flow as per Phase 4 spec.
            # If we needed to assign boolean result, we'd emit something like:
            # temp_cond = ... evaluate y ...
            # result_place = 1
            # IF temp_cond == 0 THEN L_skip
            # result_place = 0
            # REM L_skip
            # For now, error if 'not' is used outside condition context implicitly.
            raise CodeGenError("'not' operator can only be used in conditions for code generation")
        else:
            raise CodeGenError(f"Unknown unary operator: {node.operator}")

        return result_place

    def _visit_BinaryOperationNode(self, node: BinaryOperationNode) -> str:
        # Check node type for control flow vs arithmetic
        node_type = self.node_types.get(id(node))
        if node_type == 'boolean' and node.operator in ('and', 'or'):
            # Logical operators are handled by short-circuiting in control flow
            raise CodeGenError(f"'{node.operator}' operator can only be used in conditions for code generation")

        # Arithmetic or Comparison
        left_place = self._visit(node.left_operand)
        right_place = self._visit(node.right_operand)
        result_place = self._new_temp()
        op_symbol = ""

        op_map = {
            'plus': '+', 'minus': '-', 'mult': '*', 'div': '/', # [cite: 2736-2751]
            'eq': '=', '>': '>'                                # [cite: 2721-2724, 2725-2728]
        }

        if node.operator in op_map:
            op_symbol = op_map[node.operator]
            self._emit(f"{result_place} = {left_place} {op_symbol} {right_place}") # 
        else:
            raise CodeGenError(f"Unknown or misplaced binary operator: {node.operator}")

        # Note: Comparisons like eq/> generate a numeric result (0 or 1 usually),
        # but the spec treats them as boolean *conditions*. The IF instruction handles this.
        # We generate the comparison result into a temp; the IF will check it.
        return result_place

    # --- Control Flow ---

    def _visit_IfBranchNode(self, node: IfBranchNode):
        label_then = self._new_label()
        label_else = self._new_label() if node.else_branch else None
        label_exit = self._new_label()

        # Generate code for condition, jumping accordingly
        self._generate_conditional_jump(node.condition, label_then, label_else or label_exit) # Use exit label if no else

        if node.else_branch:
             # --- If-Then-Else Translation (modified from textbook) --- 
            # (Condition code already generated)
            # Else block code comes first
            self._visit(node.else_branch)
            self._emit(f"GOTO {label_exit}") # Jump over the 'then' block
            self._emit(f"REM {label_then}") # Label for 'then' block
            self._visit(node.then_branch)
            self._emit(f"REM {label_exit}") # Label after the statement
        else:
             # --- If-Then Translation (modified from textbook) --- 
            # (Condition code already generated, jumps to label_exit if false)
            self._emit(f"GOTO {label_exit}") # Explicit jump if condition was false (simpler than textbook's implicit fallthrough)
            self._emit(f"REM {label_then}") # Label for 'then' block
            self._visit(node.then_branch)
            self._emit(f"REM {label_exit}") # Label after the statement


    def _visit_WhileLoopNode(self, node: WhileLoopNode):
        label_cond = self._new_label()
        label_body = self._new_label()
        label_exit = self._new_label()

        self._emit(f"REM {label_cond}") # Label for condition check [cite: 2702-2704]
        # Generate condition check, jump to body or exit
        self._generate_conditional_jump(node.condition, label_body, label_exit)

        self._emit(f"REM {label_body}") # Label for loop body [cite: 2702-2704]
        self._visit(node.body)
        self._emit(f"GOTO {label_cond}") # Jump back to condition check

        self._emit(f"REM {label_exit}") # Label after the loop [cite: 2702-2704]

    def _visit_DoUntilLoopNode(self, node: DoUntilLoopNode):
        label_body = self._new_label()
        label_exit = self._new_label() # May not be strictly needed if last label

        self._emit(f"REM {label_body}")
        self._visit(node.body)

        # Evaluate condition specifically for jump if false
        cond_place = self._visit(node.condition) # Assumes condition evaluates to temp
        # Jump back to body if condition is FALSE (e.g., result is 0)
        self._emit(f"IF {cond_place} = 0 THEN {label_body}")
        # If condition is true, execution falls through to here (exit)
        # Optionally emit exit label if needed elsewhere: self._emit(f"REM {label_exit}")


    def _generate_conditional_jump(self, condition_node: TermNode, label_true: str, label_false: str, negate: bool = False):
        """
        Generates IR code for evaluating a condition and jumping.
        Handles simple atoms, comparisons, logical operators (and/or/not).
        'negate' swaps the true/false labels effectively.
        """
        if negate:
            label_true, label_false = label_false, label_true

        # Case 1: Condition is already a parenthesized term (op or comparison)
        if isinstance(condition_node.value, ParenTermNode):
            inner_node = condition_node.value.term
            # Case 1a: (not TERM)
            if isinstance(inner_node, UnaryOperationNode) and inner_node.operator == 'not':
                # Translate the inner term but swap true/false labels [cite: 2719-2720]
                self._generate_conditional_jump(inner_node.operand, label_false, label_true) # Note swapped labels

            # Case 1b: (TERM BINOP TERM) - Comparison or Logical
            elif isinstance(inner_node, BinaryOperationNode):
                op = inner_node.operator
                # Logical AND [cite: 2732-2735]
                if op == 'and':
                    label_second_cond = self._new_label()
                    # If first condition is false, jump directly to false label
                    self._generate_conditional_jump(inner_node.left_operand, label_second_cond, label_false)
                    self._emit(f"REM {label_second_cond}")
                    # If second condition is false, jump to false label
                    self._generate_conditional_jump(inner_node.right_operand, label_true, label_false)
                # Logical OR [cite: 2732-2735]
                elif op == 'or':
                    label_second_cond = self._new_label()
                    # If first condition is true, jump directly to true label
                    self._generate_conditional_jump(inner_node.left_operand, label_true, label_second_cond)
                    self._emit(f"REM {label_second_cond}")
                    # If second condition is true, jump to true label
                    self._generate_conditional_jump(inner_node.right_operand, label_true, label_false)
                # Comparison (eq, >) [cite: 2689-2690, 2696-2697]
                elif op in ('eq', '>'):
                    left_place = self._visit(inner_node.left_operand)
                    right_place = self._visit(inner_node.right_operand)
                    op_symbol = '=' if op == 'eq' else '>'
                    # Emit the IF THEN jump (REM label comes later)
                    self._emit(f"IF {left_place} {op_symbol} {right_place} THEN {label_true}")
                    # Implicit fallthrough is jump to false label, make it explicit if needed by caller
                else: # Should be arithmetic op, invalid in condition
                     raise CodeGenError(f"Arithmetic operator '{op}' used as condition")

            else: # Should not happen if AST is correct
                 raise CodeGenError("Unexpected node inside ParenTermNode for condition")

        # Case 2: Condition is an Atom (variable or number)
        elif isinstance(condition_node.value, AtomNode):
             # Treat non-zero as true, zero as false (common C-like convention)
             # Although SPL types PDF implies conditions *must* be boolean results
             # Let's assume the type checker ensures this atom holds a boolean result (0 or 1)
            atom_place = self._visit(condition_node.value)
            # Compare against 0
            self._emit(f"IF {atom_place} > 0 THEN {label_true}") # Assuming 1 is true, 0 is false
            # Implicit fallthrough is jump to false label

        else:
             raise CodeGenError("Unexpected condition node type")


    # --- Function/Procedure Calls ---

    def _visit_ProcedureCallNode(self, node: ProcedureCallNode):
        arg_places = [self._visit(arg) for arg in node.arguments.arguments]
        # <<< SIMPLIFY: Use annotation from node.name >>>
        if node.name.symbol_info is None or node.name.symbol_info.kind != 'proc':
            # This check is mainly for robustness during codegen debugging
            raise CodeGenError(f"Procedure VarNode '{node.name.name}' lacks valid symbol_info annotation.")
        proc_unique_name = node.name.symbol_info.unique_name
        # <<< SIMPLIFY END >>>
        call_args = ", ".join(arg_places)
        dummy_target = self._new_temp()
        self._emit(f"{dummy_target} = CALL {proc_unique_name}({call_args})")

    def _visit_FunctionCallNode(self, node: FunctionCallNode) -> str:
        arg_places = [self._visit(arg) for arg in node.arguments.arguments]
        # <<< SIMPLIFY: Use annotation from node.name >>>
        if node.name.symbol_info is None or node.name.symbol_info.kind != 'func':
            # Robustness check
            raise CodeGenError(f"Function VarNode '{node.name.name}' lacks valid symbol_info annotation.")
        func_unique_name = node.name.symbol_info.unique_name
        # <<< SIMPLIFY END >>>
        call_args = ", ".join(arg_places)
        result_place = self._new_temp()
        self._emit(f"{result_place} = CALL {func_unique_name}({call_args})")
        return result_place


    def _visit_VarNode(self, node: VarNode) -> str:
        """Returns the unique IR name directly from the node's annotation."""
        if node.symbol_info is None:
            # This should not happen if semantic analysis ran correctly
            raise CodeGenError(f"CodeGen: VarNode for '{node.name}' lacks symbol_info annotation.")
        return node.symbol_info.unique_name

    # Nodes not directly generating code but visited:
    def _visit_ProgramNode(self, node: ProgramNode): self._visit(node.main)
    def _visit_InputNode(self, node: InputNode): pass # Processed by callers
    def _visit_VariableDeclsNode(self, node: VariableDeclsNode): pass # Only affects symbol table
    def _visit_ProcDefsNode(self, node: ProcDefsNode): pass # Processed during semantic analysis
    def _visit_FuncDefsNode(self, node: FuncDefsNode): pass # Processed during semantic analysis
    def _visit_ProcedureDefNode(self, node: ProcedureDefNode): pass # Handled via inlining later
    def _visit_FunctionDefNode(self, node: FunctionDefNode): pass # Handled via inlining later
    def _visit_BodyNode(self, node: BodyNode): self._visit(node.algorithm) # Locals don't generate code
    def _visit_Max3Node(self, node: Max3Node): pass # Only affects symbol table/params