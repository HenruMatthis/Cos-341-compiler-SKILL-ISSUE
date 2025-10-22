1. Clone / unzip
cd Cos-341-compiler-SKILL-ISSUE-main

2. Run a full semantic check
python Tests/test_semantic.py
(35 tests → 100 % pass)

3. One-liner in your own script
    from lexer import Lexer
    from parser_spl import Parser
    from semantic_analyzer import SemanticAnalyzer

    src = open("myfile.spl").read()
    tokens = list(Lexer().tokenize(src))
    ast    = Parser(tokens).parse()
    SemanticAnalyzer().analyze(ast)   # raises SemanticError if ill-formed
    Done – AST is scope- and type-correct, symbol table ready for IR generation
