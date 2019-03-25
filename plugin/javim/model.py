from enumeration import Enum
from javalang import tokenizer, parser

from tree_sitter_api import Parser, InputEdit, Point
from tree_sitter_java import tree_sitter_java

class EditOperation(Enum):

    INSERT = 0
    REPLACE = 1
    DELETE = 2

class SourceFile():

    def __init__(self, vim, path, buffer):
        self.vim = vim
        self.path = path
        self.buffer = buffer
        self.line_count = len(self.buffer)
        self.parser = Parser()
        self.parser.set_language(tree_sitter_java())
        self.tree = parser.parse(self.buffer[:])

    def process_delete(self, start_row, start_col, start_byte, text):
        edit = InputEdit()
        edit.start_byte = start_byte
        edit.old_end_byte = start_byte + len(text)
        edit.new_end_byte = start_byte
        edit.start_point = Point()
        edit.start_point.row = start_row
        edit.start_point.column = start_col
        
        line_offset = text.count("\n")
        col_offset = len(text)
        if line_offset:
            last_line = text[text.rindex("\n")+1:]
            col_offset = len(last_line)
        
        edit.old_end_point = Point()
        edit.old_end_point.row = start_row + line_offset
        if line_offset:
            edit.old_end_point.column = col_offset
        else:
            edit.old_end_point.column = start_col + col_offset

        edit.new_end_point = edit.start_point

        self.tree.edit(edit)
        self.tree = self.parser.parse_string(self.buffer[:], self.tree)

    def process_insert(self, start_row, start_col, start_byte, text):
        edit = InputEdit()
        edit.start_byte = start_byte
        edit.old_end_byte = start_byte
        edit.new_end_byte = start_byte + len(text)

        edit.start_point = Point()
        edit.start_point.row = start_row
        edit.start_point.column = start_col
        
        edit.old_end_point = edit.start_point

        edit.new_end_point = Point()

        line_offset = text.count("\n")
        if line_offset:
            last_line = text[text.rindex("\n")+1:]
            edit.new_end_point.row = start_row + line_offset
            edit.new_end_point.column = len(last_line)
        else:
            edit.new_end_point.row = start_row
            edit.new_end_point.column = start_col + len(text)

        self.tree.edit(edit)
        self.tree = self.parser.parse_string(self.buffer[:], self.tree)


    def compute_change(self, start_row, start_col):
        line_count = len(self.buffer)
        edit = InputEdit()
        if line_count > self.line_count:
            # TODO: Handle inserted lines
            pass
        elif line_count < self.line_count:
            # TODO: Handle removed lines
            pass
        else:
            # TODO: handle changed lines
            pass
        self.line_count = line_count
