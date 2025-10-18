from lexer import Lexer, Token
from syntax_tree import ASTNode

class Parser:
    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token('EOF', None, -1, -1, -1)

    def eat(self, expected_type=None):
        tok = self.peek()
        if expected_type and tok.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {tok.type} at line {tok.line}")
        if tok.type == 'EOF' and expected_type:
            raise SyntaxError(f"Unexpected end of file. Expected {expected_type}.")
        self.pos += 1
        return tok

    def parse_program(self):
        self.eat('GLOB')
        self.eat('LBRACE')
        globals_node = ASTNode('GLOBALS', self.parse_variables().children)
        self.eat('RBRACE')
        self.eat('PROC')
        self.eat('LBRACE')
        procdefs_node = self.parse_procdefs()
        self.eat('RBRACE')
        self.eat('FUNC')
        self.eat('LBRACE')
        funcdefs_node = self.parse_funcdefs()
        self.eat('RBRACE')
        self.eat('MAIN')
        self.eat('LBRACE')
        mainprog_node = self.parse_mainprog()
        self.eat('RBRACE')
        return ASTNode('SPL_PROG', [globals_node, procdefs_node, funcdefs_node, mainprog_node])

    def parse_variables(self):
        vars_list = []
        while self.peek().type == 'ID':
            var_name = self.eat('ID')
            vars_list.append(ASTNode('VAR', value=var_name.value))
        return ASTNode('VARIABLES', vars_list)
    
    def parse_procdefs(self):
        procs = []
        while self.peek().type == 'ID':
            procs.append(self.parse_pdef())
        return ASTNode('PROCDEFS', procs)

    def parse_funcdefs(self):
        funcs = []
        while self.peek().type == 'ID':
            funcs.append(self.parse_fdef())
        return ASTNode('FUNCDEFS', funcs)

    def parse_pdef(self):
        name = self.eat('ID')
        self.eat('LPAREN')
        params = self.parse_param()
        self.eat('RPAREN')
        self.eat('LBRACE')
        body = self.parse_body()
        self.eat('RBRACE')
        return ASTNode('PDEF', [params, body], value=name.value)

    def parse_fdef(self):
        name = self.eat('ID')
        self.eat('LPAREN')
        params = self.parse_param()
        self.eat('RPAREN')
        self.eat('LBRACE')
        body = self.parse_body()
        if self.peek().type == 'SEMI':
            self.eat('SEMI')
        if self.peek().type != 'RETURN':
            tok = self.peek()
            raise SyntaxError(f"Missing 'return' statement before closing brace at line {tok.line}")
        self.eat('RETURN')
        atom = self.parse_atom()
        self.eat('RBRACE')
        return ASTNode('FDEF', [params, body, atom], value=name.value)

    def parse_mainprog(self):
        self.eat('VAR')
        self.eat('LBRACE')
        vars_node = self.parse_variables()
        self.eat('RBRACE')
        algo_node = self._parse_algo_required()
        return ASTNode('MAINPROG', [vars_node, algo_node])

    def parse_param(self):
        params = []
        while self.peek().type == 'ID':
            param = self.eat('ID')
            params.append(ASTNode('PARAM', value=param.value))
        return ASTNode('PARAM', params)

    def parse_maxthree(self):
        vars_list = []
        count = 0
        while self.peek().type == 'ID':
            if count >= 3:
                tok = self.peek()
                raise SyntaxError(f"Too many local variables (max 3). Unexpected '{tok.value}' at line {tok.line}")
            name = self.eat('ID')
            vars_list.append(ASTNode('VAR', value=name.value))
            count += 1
        return ASTNode('MAXTHREE', vars_list)

    def parse_body(self):
        if self.peek().type == 'LOCAL':
            self.eat('LOCAL')
            self.eat('LBRACE')
            locals_node = self.parse_maxthree()
            self.eat('RBRACE')
        else:
            locals_node = ASTNode('MAXTHREE', []) 
        algo_node = self._parse_algo_required()
        return ASTNode('BODY', [locals_node, algo_node])

    def _parse_algo_required(self):
        algo_node = self.parse_algo()
        if not algo_node.children:
            line = self.peek().line
            raise SyntaxError(f"ALGO cannot be empty as per grammar rule. An instruction must be present. (Line {line})")
        return algo_node
        
    def parse_algo(self):
        instrs = []
        while self.peek().type not in ('RBRACE', 'RETURN', 'EOF'):
            if self.peek().type == 'SEMI':
                self.eat('SEMI')
                continue
            instrs.append(self.parse_instr())
            if self.peek().type == 'SEMI':
                self.eat('SEMI')
            elif self.peek().type not in ('RBRACE', 'RETURN', 'EOF'):
                raise SyntaxError(f"Expected SEMI, RBRACE, or RETURN after instruction, got {self.peek().type} at line {self.peek().line}")
        return ASTNode('ALGO', instrs)

    def parse_instr(self):
        tok = self.peek()
        if tok.type == 'HALT':
            self.eat('HALT')
            return ASTNode('INSTR', value='halt')
        elif tok.type == 'PRINT':
            self.eat('PRINT')
            output_node = self.parse_output()
            return ASTNode('PRINT', [output_node])
        elif tok.type in ('WHILE', 'DO'): 
            return self.parse_loop()
        elif tok.type == 'IF':
            return self.parse_branch()
        elif tok.type == 'ID':
            name = self.eat('ID')
            next_tok = self.peek()
            if next_tok.type in ('EOF', 'SEMI', 'RBRACE', 'RETURN'):
                return ASTNode('INSTR_NOOP', value=name.value)
            elif next_tok.type == 'ASSIGN':
                self.eat('ASSIGN')
                if self.peek().type == 'ID' and self.tokens[self.pos + 1].type == 'LPAREN':
                    func_name = self.eat('ID')
                    self.eat('LPAREN')
                    input_node = self.parse_input()
                    self.eat('RPAREN')
                    return ASTNode('ASSIGN_FCALL', [ASTNode('VAR_REF', value=name.value), ASTNode('CALL', [input_node], value=func_name.value)])
                else:
                    term_node = self.parse_term()
                    return ASTNode('ASSIGN_TERM', [ASTNode('VAR_REF', value=name.value), term_node])
            elif next_tok.type == 'LPAREN':
                self.eat('LPAREN')
                input_node = self.parse_input()
                self.eat('RPAREN')
                return ASTNode('INSTR_PCALL', [input_node], value=name.value)
            else:
                raise SyntaxError(f"Expected ASSIGN or LPAREN after identifier '{name.value}', got {next_tok.type} at line {next_tok.line}")
        else:
            raise SyntaxError(f"Unexpected token {tok.type} at line {tok.line} (expected instruction)")

    def parse_loop(self):
        if self.peek().type == 'WHILE':
            self.eat('WHILE')
            term = self.parse_term()
            self.eat('LBRACE')
            algo = self._parse_algo_required()
            self.eat('RBRACE')
            return ASTNode('LOOP', [term, algo], value='while')
        elif self.peek().type == 'DO':
            self.eat('DO')
            self.eat('LBRACE')
            algo = self._parse_algo_required()
            self.eat('RBRACE')
            self.eat('UNTIL')
            term = self.parse_term()
            return ASTNode('LOOP', [algo, term], value='do-until')

    def parse_branch(self):
        self.eat('IF')
        term = self.parse_term()
        self.eat('LBRACE')
        if_algo = self._parse_algo_required()
        self.eat('RBRACE')
        if self.peek().type == 'ELSE':
            self.eat('ELSE')
            self.eat('LBRACE')
            else_algo = self._parse_algo_required()
            self.eat('RBRACE')
            return ASTNode('BRANCH', [term, if_algo, else_algo])
        return ASTNode('BRANCH', [term, if_algo])

    def parse_term(self):
        tok = self.peek()
        if tok.type in ('ID', 'NUMBER'):
            return self.parse_atom()
        elif tok.type == 'LPAREN':
            self.eat('LPAREN')
            if self.peek().type in ('NEG_WORD', 'NOT_WORD'): 
                unop = self.eat(self.peek().type)
                term = self.parse_term()
                self.eat('RPAREN')
                return ASTNode('TERM', [term], value=f'unop:{unop.type}')
            left = self.parse_term()
            binop_tok = self.peek()
            VALID_BINOPS = (
                'EQ_WORD', 'GT', 'LT', 'GE', 'LE',
                'OR_WORD', 'AND_WORD', 
                'PLUS_WORD', 'MINUS_WORD', 'MULT_WORD', 'DIV_WORD'
            )
            if binop_tok.type not in VALID_BINOPS:
                raise SyntaxError(f"Expected binary operator, got {binop_tok.type} at line {binop_tok.line}")
            binop = self.eat(binop_tok.type)
            right = self.parse_term()
            self.eat('RPAREN')
            return ASTNode('TERM', [left, right], value=f'binop:{binop.type}')
        else:
            raise SyntaxError(f"Unexpected token {tok.type} at line {tok.line} (expected term)")

    def parse_output(self):
        if self.peek().type == 'STRING':
            return ASTNode('OUTPUT', value=self.eat('STRING').value)
        else:
            return self.parse_atom()

    def parse_input(self):
        atoms = []
        count = 0
        while self.peek().type in ('ID', 'NUMBER') and count < 3:
            atoms.append(self.parse_atom())
            count += 1
        return ASTNode('INPUT', atoms)

    def parse_atom(self):
        tok = self.peek()
        if tok.type == 'ID':
            return ASTNode('ATOM', value=self.eat('ID').value)
        elif tok.type == 'NUMBER':
            return ASTNode('ATOM', value=self.eat('NUMBER').value)
        else:
            raise SyntaxError(f"Expected ATOM at line {tok.line}")
