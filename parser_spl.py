# parser_spl.py
# (Only showing the modified _parse_algo function and dependencies)

from lexer import Lexer, Token, LexerError
from ast_nodes import *
from typing import List, Optional, Union
import re

# --- ParseError Class (keep as is) ---
class ParseError(Exception):
    def __init__(self, message, token: Optional[Token] = None):
        if token and isinstance(token, Token):
            loc = f" at line {token.line}, col {token.column}"
            val_str = f"{token.value!r}" if token.value is not None else ""
            # Safely access keywords via Lexer class
            keyword_map = {v: k for k, v in Lexer.DEFAULT_KEYWORDS.items()}
            kw_val = keyword_map.get(token.type)
            kw_info = f" (keyword '{kw_val}')" if kw_val else ""
            # Truncate long values in error message
            if len(val_str) > 20: val_str = val_str[:17] + "...'"
            val_info = f" near token {val_str} (type {token.type}{kw_info})"
            super().__init__(f"{message}{loc}{val_info}")
        elif token is not None:
             super().__init__(f"{message} near unexpected item {token!r}")
        else:
            super().__init__(message)
        self.token = token

class Parser:
    # --- __init__ to _parse_atom (keep as is) ---
    def __init__(self, tokens: List[Token]):
        if not tokens: raise ParseError("Cannot parse empty token list.")
        self.tokens = tokens
        self.current_pos = 0
        self.current_tok: Optional[Token] = self.tokens[self.current_pos]
        self._keyword_values = {v: k for k, v in Lexer.DEFAULT_KEYWORDS.items()}

    def _advance(self):
        self.current_pos += 1
        self.current_tok = self.tokens[self.current_pos] if self.current_pos < len(self.tokens) else None

    def _peek(self) -> Optional[Token]:
        peek_pos = self.current_pos + 1
        return self.tokens[peek_pos] if peek_pos < len(self.tokens) else None

    def _match(self, expected_type: str, expected_value: Optional[str] = None):
        tok = self.current_tok
        if not tok or tok.type == 'EOF':
            if expected_type == 'EOF': return tok
            last_token = self.tokens[self.current_pos-1] if self.current_pos > 0 else None
            raise ParseError(f"Expected token type '{expected_type}' but found end of input", token=last_token)

        if tok.type == expected_type:
            matched_token = tok
            self._advance()
            return matched_token
        else:
            expected_desc = f"'{expected_value}' (type {expected_type})" if expected_value else f"type '{expected_type}'"
            found_kw = self._keyword_values.get(tok.type)
            found_desc = f"type '{tok.type}'"
            if found_kw: found_desc += f" (keyword '{found_kw}')"
            if tok.value is not None:
                 val_str = f"{tok.value!r}"
                 if len(val_str) > 20: val_str = val_str[:17] + "...'"
                 found_desc += f" with value {val_str}"
            raise ParseError(f"Expected {expected_desc}", token=tok)

    def parse(self) -> ProgramNode:
        program_node = self._parse_spl_prog()
        self._match('EOF')
        return program_node

    def _parse_spl_prog(self) -> ProgramNode:
        self._match('GLOB', 'glob'); self._match('LBRACE'); globals_node = self._parse_variables(); self._match('RBRACE')
        self._match('PROC', 'proc'); self._match('LBRACE'); procs_node = self._parse_procdefs(); self._match('RBRACE')
        self._match('FUNC', 'func'); self._match('LBRACE'); funcs_node = self._parse_funcdefs(); self._match('RBRACE')
        self._match('MAIN', 'main'); self._match('LBRACE'); main_node = self._parse_mainprog(); self._match('RBRACE')
        return ProgramNode(globals=globals_node, procs=procs_node, funcs=funcs_node, main=main_node)

    def _parse_variables(self) -> VariableDeclsNode:
        variables = []
        while self.current_tok and self.current_tok.type == 'ID': variables.append(self._parse_var())
        return VariableDeclsNode(variables=variables)

    def _parse_var(self) -> VarNode:
        tok = self._match('ID')
        if tok.value in Lexer.DEFAULT_KEYWORDS: raise ParseError(f"Identifier cannot be a keyword: '{tok.value}'", token=tok)
        return VarNode(name=tok.value)

    def _parse_procdefs(self) -> ProcDefsNode:
        procedures = []
        while self.current_tok and self.current_tok.type == 'PDEF': procedures.append(self._parse_pdef())
        return ProcDefsNode(procedures=procedures)

    def _parse_pdef(self) -> ProcedureDefNode:
        self._match('PDEF', 'pdef'); name_node = self._parse_var(); self._match('LPAREN'); param_node = self._parse_param(); self._match('RPAREN'); self._match('LBRACE'); body_node = self._parse_body(); self._match('RBRACE')
        return ProcedureDefNode(name=name_node, params=param_node, body=body_node)

    def _parse_funcdefs(self) -> FuncDefsNode:
        functions = []
        while self.current_tok and self.current_tok.type == 'FDEF': functions.append(self._parse_fdef())
        return FuncDefsNode(functions=functions)

    def _parse_fdef(self) -> FunctionDefNode:
        self._match('FDEF', 'fdef'); name_node = self._parse_var(); self._match('LPAREN'); param_node = self._parse_param(); self._match('RPAREN'); self._match('LBRACE'); body_node = self._parse_body(); self._match('SEMICOLON'); self._match('RETURN', 'return'); atom_node = self._parse_atom(); self._match('RBRACE')
        return FunctionDefNode(name=name_node, params=param_node, body=body_node, return_atom=atom_node)

    def _parse_body(self) -> BodyNode:
        self._match('LOCAL', 'local'); self._match('LBRACE'); max3_node = self._parse_max3(); self._match('RBRACE'); algo_node = self._parse_algo()
        return BodyNode(locals=max3_node, algorithm=algo_node)

    def _parse_param(self) -> Max3Node: return self._parse_max3()

    def _parse_max3(self) -> Max3Node:
        variables = []
        if self.current_tok and self.current_tok.type == 'ID':
            variables.append(self._parse_var()) # Parse 1st
            if self.current_tok and self.current_tok.type == 'ID':
                variables.append(self._parse_var()) # Parse 2nd
                if self.current_tok and self.current_tok.type == 'ID':
                    variables.append(self._parse_var()) # Parse 3rd
                    
                    # After parsing three, check if a fourth ID exists
                    if self.current_tok and self.current_tok.type == 'ID':
                        # This is the error case
                        raise ParseError(
                            "Maximum number of variables (3) exceeded in list", 
                            token=self.current_tok
                        )
        
        return Max3Node(variables=variables)

    def _parse_mainprog(self) -> MainProgNode:
        self._match('VAR', 'var'); self._match('LBRACE'); variables_node = self._parse_variables(); self._match('RBRACE'); algo_node = self._parse_algo()
        return MainProgNode(locals=variables_node, algorithm=algo_node)

    def _parse_atom(self) -> AtomNode:
        if not self.current_tok: raise ParseError("Expected id or number")
        if self.current_tok.type == 'ID':
            tok_value = self.current_tok.value
            if tok_value in Lexer.DEFAULT_KEYWORDS: raise ParseError(f"Expected id or number but found keyword '{tok_value}'", token=self.current_tok)
            return AtomNode(value=self._parse_var())
        elif self.current_tok.type == 'NUMBER': tok = self._match('NUMBER'); return AtomNode(value=tok.value)
        else: raise ParseError("Expected identifier or number", token=self.current_tok)

    # --- REVISED _parse_algo ---
    def _parse_algo(self) -> AlgorithmNode:
        instr_start_tokens = {'HALT', 'PRINT', 'ID', 'WHILE', 'DO', 'IF'}
        algo_end_tokens = {'RBRACE', 'UNTIL', 'ELSE', 'RETURN', 'EOF'}

        if not self.current_tok or self.current_tok.type not in instr_start_tokens:
            if self.current_tok and self.current_tok.type in algo_end_tokens:
                 raise ParseError("Algorithm block cannot be empty", token=self.current_tok)
            else:
                 raise ParseError("Expected instruction to start algorithm", token=self.current_tok)

        instructions = [self._parse_instr()]

        while self.current_tok and self.current_tok.type == 'SEMICOLON':
            semicolon_token = self.current_tok
            next_tok = self._peek()

            # **REVISED FIX**: If the *next* token marks the end of the algo block
            # (e.g., RETURN, RBRACE), break *before* consuming the semicolon.
            if not next_tok or next_tok.type in algo_end_tokens:
                 break # Let the caller handle the end token (and the preceding ';')

            # If the next token can start an instruction, consume ';' and parse it
            if next_tok.type in instr_start_tokens:
                self._match('SEMICOLON')
                instructions.append(self._parse_instr())
            else: # Found semicolon, but next token is unexpected
                 self._match('SEMICOLON')
                 raise ParseError("Expected instruction after semicolon", token=self.current_tok)

        return AlgorithmNode(instructions=instructions)

    # --- _parse_instr down to _parse_branch (keep as is) ---
    def _parse_instr(self) -> ASTNode:
        if not self.current_tok: raise ParseError("Expected instruction")
        tok_type = self.current_tok.type
        if tok_type == 'HALT': self._match('HALT', 'halt'); return HaltNode()
        elif tok_type == 'PRINT': self._match('PRINT', 'print'); return PrintNode(output=self._parse_output())
        elif tok_type == 'ID': return self._parse_instr_after_id(self._parse_var())
        elif tok_type in ('WHILE', 'DO'): return self._parse_loop()
        elif tok_type == 'IF': return self._parse_branch()
        else: raise ParseError("Expected instruction start", token=self.current_tok)

    def _parse_instr_after_id(self, name_node: VarNode) -> ASTNode:
        error_token = self.current_tok
        if not error_token or error_token.type == 'EOF': raise ParseError("Expected '(' or '=' after identifier", token=error_token)
        if error_token.type == 'LPAREN': self._match('LPAREN'); args = self._parse_input(); self._match('RPAREN'); return ProcedureCallNode(name=name_node, arguments=args)
        elif error_token.type == 'ASSIGN': self._match('ASSIGN'); rhs = self._parse_assign_rhs(); return AssignmentNode(variable=name_node, rhs=rhs)
        else: raise ParseError("Expected '(' or '=' after identifier", token=error_token)

    def _parse_assign_rhs(self) -> ASTNode:
        if not self.current_tok: raise ParseError("Expected id, number, or '(' for RHS")
        if self.current_tok.type == 'ID':
            id_node = self._parse_var()
            if self.current_tok and self.current_tok.type == 'LPAREN': self._match('LPAREN'); args = self._parse_input(); self._match('RPAREN'); return FunctionCallNode(name=id_node, arguments=args)
            return AtomNode(value=id_node)
        elif self.current_tok.type == 'NUMBER': return self._parse_atom()
        elif self.current_tok.type == 'LPAREN': return self._parse_parens_term()
        else: raise ParseError("Expected id, number, or '(' for RHS", token=self.current_tok)

    def _parse_parens_term(self) -> ParenTermNode:
        self._match('LPAREN')
        if not self.current_tok: raise ParseError("Expected content inside ()")
        if self.current_tok.type in ('NEG_WORD', 'NOT'): op = self._parse_unop(); term_node = self._parse_term(); node = UnaryOperationNode(operator=op, operand=term_node)
        else: term1 = self._parse_term(); op = self._parse_binop(); term2 = self._parse_term(); node = BinaryOperationNode(left_operand=term1, operator=op, right_operand=term2)
        self._match('RPAREN'); return ParenTermNode(term=node)

    def _parse_term(self) -> TermNode:
        if not self.current_tok: raise ParseError("Expected atom or '('")
        if self.current_tok.type in ('ID', 'NUMBER'): return TermNode(value=self._parse_atom())
        elif self.current_tok.type == 'LPAREN': return TermNode(value=self._parse_parens_term())
        else: raise ParseError("Expected id, number, or '('", token=self.current_tok)

    def _parse_unop(self) -> str:
        if not self.current_tok: raise ParseError("Expected 'neg' or 'not'")
        if self.current_tok.type == 'NEG_WORD': self._match('NEG_WORD', 'neg'); return 'neg'
        elif self.current_tok.type == 'NOT': self._match('NOT', 'not'); return 'not'
        else: raise ParseError("Expected 'neg' or 'not'", token=self.current_tok)

    def _parse_binop(self) -> str:
        if not self.current_tok: raise ParseError("Expected binary operator")
        op_map = {'EQ_WORD': 'eq', 'GT': '>', 'OR': 'or', 'AND': 'and', 'PLUS_WORD': 'plus', 'MINUS_WORD': 'minus', 'MULT_WORD': 'mult', 'DIV_WORD': 'div'}
        tok_type = self.current_tok.type
        if tok_type in op_map: self._match(tok_type); return op_map[tok_type]
        else: raise ParseError(f"Expected binary operator", token=self.current_tok)

    def _parse_output(self) -> Union[AtomNode, str]:
        if not self.current_tok: raise ParseError("Expected atom or string for print")
        if self.current_tok.type in ('ID', 'NUMBER'): return self._parse_atom()
        elif self.current_tok.type == 'STRING': tok = self._match('STRING'); return tok.value
        else: raise ParseError("Expected id, number, or string", token=self.current_tok)

    def _parse_input(self) -> InputNode:
        arguments = []
        if self.current_tok and self.current_tok.type in ('ID', 'NUMBER'): arguments.append(self._parse_atom())
        if self.current_tok and self.current_tok.type in ('ID', 'NUMBER'): arguments.append(self._parse_atom())
        if self.current_tok and self.current_tok.type in ('ID', 'NUMBER'): arguments.append(self._parse_atom())
        return InputNode(arguments=arguments)

    def _parse_loop(self) -> ASTNode:
        if not self.current_tok: raise ParseError("Expected 'while' or 'do'")
        if self.current_tok.type == 'WHILE': self._match('WHILE', 'while'); condition = self._parse_term(); self._match('LBRACE'); body = self._parse_algo(); self._match('RBRACE'); return WhileLoopNode(condition=condition, body=body)
        elif self.current_tok.type == 'DO': self._match('DO', 'do'); self._match('LBRACE'); body = self._parse_algo(); self._match('RBRACE'); self._match('UNTIL', 'until'); condition = self._parse_term(); return DoUntilLoopNode(body=body, condition=condition)
        else: raise ParseError("Expected 'while' or 'do'", token=self.current_tok)

    def _parse_branch(self) -> IfBranchNode:
        self._match('IF', 'if'); condition = self._parse_term(); self._match('LBRACE'); then_algo = self._parse_algo(); self._match('RBRACE'); else_algo = None
        if self.current_tok and self.current_tok.type == 'ELSE': self._match('ELSE', 'else'); self._match('LBRACE'); else_algo = self._parse_algo(); self._match('RBRACE')
        return IfBranchNode(condition=condition, then_branch=then_algo, else_branch=else_algo)