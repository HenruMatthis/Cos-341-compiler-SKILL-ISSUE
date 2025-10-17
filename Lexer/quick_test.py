from lexer import Lexer

lex = Lexer()
src = 'glob counter = 0\nprint "hello\\nworld"'
for tok in lex.tokenize(src):
    print(tok)
