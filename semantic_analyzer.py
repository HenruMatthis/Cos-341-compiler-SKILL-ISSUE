# semantic_analyzer.py
"""
Performs scope checking (Task 5) and type checking (Task 6) on the SPL AST.
Multi-scope snapshot version – drop-in replacement.
"""

from typing import Optional, List, Set, Dict, Any, Tuple
from ast_nodes import *
from symbol_table import SymbolTable, SymbolInfo, SymbolTableError


class SemanticError(Exception):
    """Exception raised for semantic errors during analysis."""
    def __init__(self, message: str, node: Optional[ASTNode] = None):
        self.message = message
        self.node = node
        super().__init__(message)


class SemanticAnalyzer:
    """
    Performs scope checking (Task 5) and type checking (Task 6) on the AST.
    """

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[str] = []
        self.current_function_name: Optional[str] = None

        # Type information storage (annotates nodes)
        self.node_types: Dict[int, str] = {}  # Maps node id -> type ('numeric' or 'boolean')

        # NEW: collect every scope stack state we ever see
        self._scope_history: List[Tuple[str, List[Dict[str, SymbolInfo]]]] = []

    # ==================== Main Entry Point ====================

    def analyze(self, ast: ProgramNode) -> SymbolTable:
        """
        Main entry point for semantic analysis.
        Returns the populated symbol table if successful.
        Raises SemanticError if any semantic errors are found.
        """
        try:
            # Visit the entire AST
            self._visit_program(ast)

            # If we collected any errors, raise them
            if self.errors:
                raise SemanticError("\n".join(self.errors))

            final_symbol_table_state = self.symbol_table
            return final_symbol_table_state

        except SymbolTableError as e:
            raise SemanticError(f"Symbol table error: {e}")

    # ==================== Task 5: Scope Checking ====================

    def _visit_program(self, node: ProgramNode):
        """Visit the root program node and establish global scope."""
        is_toplevel_call = self.symbol_table.current_scope_level() == 0
        if is_toplevel_call:
            self.symbol_table.enter_scope("Global", node)
        # Enter global scope
        self.symbol_table.enter_scope("Global", node)

        # 1. Declare all global variables
        self._visit_variable_decls(node.globals, is_global=True)

        # 2. Declare all procedures (just signatures)
        self._declare_procedures(node.procs)

        # 3. Declare all functions (just signatures)
        self._declare_functions(node.funcs)

        # 4. Check for global name clashes (var/proc/func conflicts)
        try:
            self.symbol_table.check_no_global_name_clashes()
        except SymbolTableError as e:
            raise SemanticError(f"Global scope violation: {e}")

        # 5. Now visit procedure bodies
        self._visit_procedure_defs(node.procs)

        # 6. Visit function bodies
        self._visit_function_defs(node.funcs)

        # 7. Visit main program
        self._visit_main_prog(node.main)

        # FIXED: snapshot BEFORE exiting global scope
        self._snapshot_now("Global – before exit")
        # Exit global scope
        self.symbol_table.exit_scope()

    def _visit_variable_decls(self, node: VariableDeclsNode, is_global: bool = False):
        """Declare variables and check for duplicates in current scope."""
        seen_names = set()

        for var_node in node.variables:
            var_name = var_node.name

            # Check for duplicate in this declaration list
            if var_name in seen_names:
                raise SemanticError(
                    f"Duplicate variable declaration '{var_name}' in the same scope"
                )
            seen_names.add(var_name)

            # Declare in symbol table (default type is 'numeric')
            try:
                self.symbol_table.declare_var(var_name, var_node, decl_type="numeric")
            except SymbolTableError as e:
                raise SemanticError(str(e))

    def _declare_procedures(self, node: ProcDefsNode):
        """Declare all procedure signatures in current (global) scope."""
        seen_names = set()

        for proc_def in node.procedures:
            proc_name = proc_def.name.name

            if proc_name in seen_names:
                raise SemanticError(
                    f"Duplicate procedure declaration '{proc_name}'"
                )
            seen_names.add(proc_name)

            try:
                self.symbol_table.declare_proc(proc_name, proc_def)
            except SymbolTableError as e:
                raise SemanticError(str(e))

    def _declare_functions(self, node: FuncDefsNode):
        """Declare all function signatures in current (global) scope."""
        seen_names = set()

        for func_def in node.functions:
            func_name = func_def.name.name

            if func_name in seen_names:
                raise SemanticError(
                    f"Duplicate function declaration '{func_name}'"
                )
            seen_names.add(func_name)

            try:
                self.symbol_table.declare_func(func_name, func_def)
            except SymbolTableError as e:
                raise SemanticError(str(e))

    def _visit_procedure_defs(self, node: ProcDefsNode):
        """Visit all procedure definitions and check their bodies."""
        for proc_def in node.procedures:
            self._visit_procedure_def(proc_def)

    def _visit_procedure_def(self, node: ProcedureDefNode):
        """Visit a single procedure definition."""
        proc_name = node.name.name

        # Enter procedure scope
        self.symbol_table.enter_scope("Procedure", node)

        # Declare parameters
        param_names = self._visit_parameters(node.params)

        # Visit body (which includes local variables and algorithm)
        local_names = self._visit_body(node.body, param_names)

        self._snapshot_now(f"Procedure '{proc_name}' – end")
        # Exit procedure scope
        self.symbol_table.exit_scope()

    def _visit_function_defs(self, node: FuncDefsNode):
        """Visit all function definitions and check their bodies."""
        for func_def in node.functions:
            self._visit_function_def(func_def)

    def _visit_function_def(self, node: FunctionDefNode):
        """Visit a single function definition."""
        func_name = node.name.name
        self.current_function_name = func_name

        # Enter function scope
        self.symbol_table.enter_scope("Function", node)

        # Declare parameters
        param_names = self._visit_parameters(node.params)

        # Visit body (which includes local variables and algorithm)
        local_names = self._visit_body(node.body, param_names)

        # Check return atom type (must be numeric or variable)
        return_type = self._visit_atom(node.return_atom)
        if return_type != "numeric":
            raise SemanticError(
                f"Function '{func_name}' must return a numeric value, but returns {return_type}"
            )

        self._snapshot_now(f"Function '{func_name}' – end")
        # Exit function scope
        self.symbol_table.exit_scope()
        self.current_function_name = None

    def _visit_parameters(self, node: Max3Node) -> List[str]:
        """
        Declare parameters and return list of parameter names.
        Check for duplicate parameters.
        """
        param_names = []
        seen_names = set()

        for var_node in node.variables:
            param_name = var_node.name

            if param_name in seen_names:
                raise SemanticError(
                    f"Duplicate parameter '{param_name}' in parameter list"
                )
            seen_names.add(param_name)
            param_names.append(param_name)

            # Declare as parameter (default numeric)
            try:
                self.symbol_table.declare_param(param_name, var_node, decl_type="numeric")
            except SymbolTableError as e:
                raise SemanticError(str(e))

        return param_names

    def _visit_body(self, node: BodyNode, param_names: List[str]) -> List[str]:
        """
        Visit a function/procedure body.
        Returns list of local variable names.
        """
        # Declare local variables (Max3Node)
        local_names = []
        seen_names = set()

        for var_node in node.locals.variables:
            local_name = var_node.name

            if local_name in seen_names:
                raise SemanticError(
                    f"Duplicate local variable '{local_name}'"
                )
            seen_names.add(local_name)
            local_names.append(local_name)

            # Declare in symbol table
            try:
                self.symbol_table.declare_var(local_name, var_node, decl_type="numeric")
            except SymbolTableError as e:
                raise SemanticError(str(e))

        # Check for shadowing of parameters
        try:
            self.symbol_table.check_no_shadowing_of_params(param_names, local_names)
        except SymbolTableError as e:
            raise SemanticError(f"Shadowing error: {e}")

        # Visit the algorithm
        self._visit_algorithm(node.algorithm)

        return local_names

    def _visit_main_prog(self, node: MainProgNode):
        """Visit the main program block."""
        # Enter main scope
        self.symbol_table.enter_scope("Main", node)

        # Declare main's local variables
        self._visit_variable_decls(node.locals)

        # Visit the algorithm
        self._visit_algorithm(node.algorithm)

        self._snapshot_now("Main – end")
        # Exit main scope
        self.symbol_table.exit_scope()

    def _visit_algorithm(self, node: AlgorithmNode):
        """Visit an algorithm (sequence of instructions)."""
        for instruction in node.instructions:
            self._visit_instruction(instruction)

    def _visit_instruction(self, node: ASTNode):
        """Dispatch to appropriate instruction visitor."""
        if isinstance(node, HaltNode):
            pass  # No checks needed for halt

        elif isinstance(node, PrintNode):
            self._visit_print(node)

        elif isinstance(node, AssignmentNode):
            self._visit_assignment(node)

        elif isinstance(node, ProcedureCallNode):
            self._visit_procedure_call(node)

        elif isinstance(node, WhileLoopNode):
            self._visit_while_loop(node)

        elif isinstance(node, DoUntilLoopNode):
            self._visit_do_until_loop(node)

        elif isinstance(node, IfBranchNode):
            self._visit_if_branch(node)

        else:
            raise SemanticError(f"Unknown instruction type: {type(node).__name__}")

    # ==================== Task 6: Type Checking ====================

    def _visit_print(self, node: PrintNode):
        """
        Visit print statement.
        Output can be: ATOM (id or number) or string literal.
        """
        if isinstance(node.output, str):
            # String literal - no type checking needed
            pass
        elif isinstance(node.output, AtomNode):
            # Type check the atom
            self._visit_atom(node.output)
        else:
            raise SemanticError(f"Invalid print output type: {type(node.output)}")

    def _visit_assignment(self, node: AssignmentNode):
        """
        Visit assignment: VAR = RHS
        - Variable must be declared
        - Variable must be numeric (all variables in SPL are numeric)
        - RHS must evaluate to numeric
        """
        var_name = node.variable.name
        var_node = node.variable

        # Check variable is declared
        var_info = self.symbol_table.lookup(var_name)
        if var_info is None:
            raise SemanticError(f"Undefined variable '{var_name}' in assignment")

        var_node.symbol_info = var_info

        # Check variable is numeric (should always be true in SPL)
        if var_info.decl_type != "numeric":
            raise SemanticError(
                f"Cannot assign to non-numeric variable '{var_name}'"
            )

        # Type check RHS
        rhs_type = self._visit_rhs(node.rhs)

        # RHS must be numeric
        if rhs_type != "numeric":
            raise SemanticError(
                f"Assignment to '{var_name}' requires numeric value, got {rhs_type}"
            )

    def _visit_rhs(self, node: ASTNode) -> str:
        """
        Visit right-hand side of assignment.
        Can be: AtomNode, FunctionCallNode, or ParenTermNode
        Returns the type ('numeric' or 'boolean')
        """
        if isinstance(node, AtomNode):
            return self._visit_atom(node)

        elif isinstance(node, FunctionCallNode):
            return self._visit_function_call(node)

        elif isinstance(node, ParenTermNode):
            return self._visit_paren_term(node)

        else:
            raise SemanticError(f"Invalid RHS type: {type(node).__name__}")

    def _visit_atom(self, node: AtomNode) -> str:
        """
        Visit an atom (id or number).
        Returns 'numeric' (all atoms in SPL are numeric).
        """
        if isinstance(node.value, int):
            # Number literal
            self._set_node_type(node, "numeric")
            return "numeric"

        elif isinstance(node.value, VarNode):
            # Variable reference
            var_node = node.value
            var_name = node.value.name
            var_info = self.symbol_table.lookup(var_name)

            if var_info is None:
                raise SemanticError(f"Undefined variable '{var_name}'")

            var_node.symbol_info = var_info

            # All variables in SPL are numeric
            self._set_node_type(node, "numeric")
            return "numeric"

        else:
            raise SemanticError(f"Invalid atom value type: {type(node.value)}")

    def _visit_function_call(self, node: FunctionCallNode) -> str:
        """
        Visit function call.
        - Function must be declared
        - Arguments must be checked
        - All functions return numeric in SPL
        """
        func_node = node.name # Get the VarNode instance
        func_name = func_node.name

        # Check function is declared
        func_info = self.symbol_table.lookup(func_name)
        if func_info is None:
            raise SemanticError(f"Undefined function '{func_name}'")

        if func_info.kind != "func":
            raise SemanticError(
                f"'{func_name}' is not a function (it's a {func_info.kind})"
            )

        # <<< ADD ANNOTATION HERE >>>
        func_node.symbol_info = func_info

        # Check arguments (This should already visit the AtomNodes within)
        self._visit_input(node.arguments)

        # Check argument count (Optional but good practice)
        # expected_param_count = len(func_info.extra.get('param_names', [])) # Assuming param names stored in extra
        # actual_arg_count = len(node.arguments.arguments)
        # if actual_arg_count != expected_param_count:
        #     raise SemanticError(f"Function '{func_name}' expects {expected_param_count} arguments, got {actual_arg_count}")

        # All functions return numeric
        self._set_node_type(node, "numeric")
        return "numeric"

    def _visit_procedure_call(self, node: ProcedureCallNode):
        """
        Visit procedure call.
        - Procedure must be declared
        - Arguments must be checked
        """
        proc_node = node.name # Get the VarNode instance
        proc_name = proc_node.name

        # Check procedure is declared
        proc_info = self.symbol_table.lookup(proc_name)
        if proc_info is None:
            raise SemanticError(f"Undefined procedure '{proc_name}'")

        if proc_info.kind != "proc":
            raise SemanticError(
                f"'{proc_name}' is not a procedure (it's a {proc_info.kind})"
            )

        # <<< ADD ANNOTATION HERE >>>
        proc_node.symbol_info = proc_info

        # Check arguments
        self._visit_input(node.arguments)

        # Check argument count (Optional but good practice)
        # expected_param_count = len(proc_info.extra.get('param_names', []))
        # actual_arg_count = len(node.arguments.arguments)
        # if actual_arg_count != expected_param_count:
        #     raise SemanticError(f"Procedure '{proc_name}' expects {expected_param_count} arguments, got {actual_arg_count}")

    def _visit_input(self, node: InputNode):
        """Visit input arguments (0-3 atoms)."""
        for arg in node.arguments:
            self._visit_atom(arg)

    def _visit_paren_term(self, node: ParenTermNode) -> str:
        """
        Visit parenthesized term.
        Returns the type of the inner term.
        """
        if isinstance(node.term, UnaryOperationNode):
            return self._visit_unary_op(node.term)
        elif isinstance(node.term, BinaryOperationNode):
            return self._visit_binary_op(node.term)
        else:
            raise SemanticError(f"Invalid term in parentheses: {type(node.term)}")

    def _visit_term(self, node: TermNode) -> str:
        """
        Visit a term (atom or parenthesized term).
        Returns the type.
        """
        if isinstance(node.value, AtomNode):
            return self._visit_atom(node.value)
        elif isinstance(node.value, ParenTermNode):
            return self._visit_paren_term(node.value)
        else:
            raise SemanticError(f"Invalid term value: {type(node.value)}")

    def _visit_unary_op(self, node: UnaryOperationNode) -> str:
        """
        Visit unary operation (neg or not).
        - 'neg' requires numeric operand, returns numeric
        - 'not' requires boolean operand, returns boolean
        """
        operator = node.operator
        operand_type = self._visit_term(node.operand)

        if operator == "neg":
            if operand_type != "numeric":
                raise SemanticError(
                    f"Operator 'neg' requires numeric operand, got {operand_type}"
                )
            self._set_node_type(node, "numeric")
            return "numeric"

        elif operator == "not":
            if operand_type != "boolean":
                raise SemanticError(
                    f"Operator 'not' requires boolean operand, got {operand_type}"
                )
            self._set_node_type(node, "boolean")
            return "boolean"

        else:
            raise SemanticError(f"Unknown unary operator: {operator}")

    def _visit_binary_op(self, node: BinaryOperationNode) -> str:
        """
        Visit binary operation.
        Type rules:
        - Arithmetic (plus, minus, mult, div): numeric × numeric → numeric
        - Comparison (eq, >): numeric × numeric → boolean
        - Logical (and, or): boolean × boolean → boolean
        """
        operator = node.operator
        left_type = self._visit_term(node.left_operand)
        right_type = self._visit_term(node.right_operand)

        # Arithmetic operators
        if operator in ("plus", "minus", "mult", "div"):
            if left_type != "numeric":
                raise SemanticError(
                    f"Operator '{operator}' requires numeric left operand, got {left_type}"
                )
            if right_type != "numeric":
                raise SemanticError(
                    f"Operator '{operator}' requires numeric right operand, got {right_type}"
                )
            self._set_node_type(node, "numeric")
            return "numeric"

        # Comparison operators
        elif operator in ("eq", ">"):
            if left_type != "numeric":
                raise SemanticError(
                    f"Operator '{operator}' requires numeric left operand, got {left_type}"
                )
            if right_type != "numeric":
                raise SemanticError(
                    f"Operator '{operator}' requires numeric right operand, got {right_type}"
                )
            self._set_node_type(node, "boolean")
            return "boolean"

        # Logical operators
        elif operator in ("and", "or"):
            if left_type != "boolean":
                raise SemanticError(
                    f"Operator '{operator}' requires boolean left operand, got {left_type}"
                )
            if right_type != "boolean":
                raise SemanticError(
                    f"Operator '{operator}' requires boolean right operand, got {right_type}"
                )
            self._set_node_type(node, "boolean")
            return "boolean"

        else:
            raise SemanticError(f"Unknown binary operator: {operator}")

    def _visit_while_loop(self, node: WhileLoopNode):
        """
        Visit while loop.
        Condition must be boolean.
        """
        condition_type = self._visit_term(node.condition)

        if condition_type != "boolean":
            raise SemanticError(
                f"While loop condition must be boolean, got {condition_type}"
            )

        self._visit_algorithm(node.body)

    def _visit_do_until_loop(self, node: DoUntilLoopNode):
        """
        Visit do-until loop.
        Condition must be boolean.
        """
        self._visit_algorithm(node.body)

        condition_type = self._visit_term(node.condition)

        if condition_type != "boolean":
            raise SemanticError(
                f"Do-until loop condition must be boolean, got {condition_type}"
            )

    def _visit_if_branch(self, node: IfBranchNode):
        """
        Visit if statement.
        Condition must be boolean.
        """
        condition_type = self._visit_term(node.condition)

        if condition_type != "boolean":
            raise SemanticError(
                f"If condition must be boolean, got {condition_type}"
            )

        self._visit_algorithm(node.then_branch)

        if node.else_branch is not None:
            self._visit_algorithm(node.else_branch)

    # ==================== Utility Methods ====================

    def _set_node_type(self, node: ASTNode, type_: str):
        """Store type information for a node."""
        self.node_types[id(node)] = type_

    def get_node_type(self, node: ASTNode) -> Optional[str]:
        """Retrieve stored type for a node."""
        return self.node_types.get(id(node))

    def _snapshot_now(self, label: str) -> None:
        """Capture current stack state and remember it."""
        self._scope_history.append((label, self.symbol_table.get_scope_snapshot()))

    def print_full_symbol_story(self) -> None:
        """Print every scope stack we ever captured."""
        print("\n" + "="*60)
        print("COMPLETE SCOPE HISTORY")
        print("="*60)
        for label, snap in self._scope_history:
            print(f"\n{label}")
            for lvl, scope in enumerate(snap, 1):
                print(f"  Scope {lvl}:")
                if not scope:
                    print("    (empty)")
                else:
                    for name, info in sorted(scope.items()):
                        print(f"    {name}: kind={info.kind}, "
                              f"type={info.decl_type}, unique={info.unique_name}")
        print("="*60)

    def print_symbol_table(self):
        """Print the symbol table for debugging."""
        print("\n" + "="*60)
        print("SYMBOL TABLE")
        print("="*60)
        print(self.symbol_table)
        print("="*60)