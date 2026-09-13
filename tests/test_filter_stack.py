from sqlparse import engine, tokens as T


class CustomLexer:
    def get_tokens(self, sql, encoding=None):
        yield T.Keyword, "CUSTOM"


def test_filter_stack_custom_lexer():
    stack = engine.FilterStack()
    stack.lexer = CustomLexer()

    statement = next(stack.run("ignored input"))

    assert str(statement) == "CUSTOM"
