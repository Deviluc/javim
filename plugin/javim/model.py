from javalang import tokenizer, parser

class SourceFile():

    def __init__(self, path, buffer):
        self.path = path
        self.buffer = buffer
        self.line_count = len(self.buffer)
        self.tokens = tokenizer.tokenize(self.buffer[:])
        self.ast = parser.parse(self.tokens)

    def compute_change(self, vim, start, end):
        line_count = len(self.buffer)
        start_row, start_col = start
        end_row, end_col = end
        if line_count > self.line_count:
            # TODO: Handle inserted lines
            pass
        elif line_count < self.line_count:
            # TODO: Handle removed lines
            pass
        else:
            # TODO: handle changed lines
            pass
