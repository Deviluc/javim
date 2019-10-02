from javim.buffer_change import BufferChangeListener, BufferChangeDispatcher
from javim.util_classes import OffsetChain, ReplaceRangeOffsetChainUpdate, DeleteOffsetChainUpdate, DelayedAction
import javim
import treelib as tl
from tempfile import mkstemp
from os import remove
from os.path import exists
from threading import Lock


from tree_sitter import Language, Parser, Tree

Language.build_library("build/langs.so", ["/home/friese/git/tree-sitter-java"])
JAVA_LANG = Language("build/langs.so", "java")
parser = Parser()
parser.set_language(JAVA_LANG)

_, tree_file = mkstemp(suffix="tree")

tree_lock = Lock()

def tree2file(tree: Tree):
    if exists(tree_file): remove(tree_file)

    def gen_index():
        i = 1
        while True:
            yield i
            i += 1
    index = gen_index()
    t = tl.Tree()
    t.create_node(tree.root_node.type, 0)

    nodes = list(map(lambda n: (n, 0), tree.root_node.children))

    while nodes:
        child_nodes = []
        for node, parent_index in nodes:
            i = next(index)
            t.create_node(node.type, i, parent=parent_index)
            for child in node.children:
                child_nodes.append((child, i))
        nodes = child_nodes
    t.save2file(tree_file)

    return tree_file

def show_tree(tree, nvim):
    if not tree_lock.acquire(False): return

    nvim.command("echom 'Acquired lock!'")
    try:
        filename = tree2file(tree)
        nr = nvim.current.window.number

        buf_nr = int(nvim.eval('bufnr("%s")' % filename))
        p_buf_nr = nvim.current.buffer.number
        if buf_nr != -1:
            nvim.command("b %i | e %% | b %i" % (buf_nr, p_buf_nr))
        else:
            nvim.command("botright 90vs | enew | e %s | setlocal autoread \"on\" | file Tree | exe %i . \"wincmd w\"" % (filename, nr))
    finally:
        tree_lock.release()
        nvim.command("echom 'Released lock!'")

class JavaAstBufferChangeListener(BufferChangeListener):

    def __init__(self, nvim):
        self.nvim = nvim
        self.buffers = dict()

    def parse_buffer(self, bufnr):
        buffer = self.nvim.buffers[bufnr]
        chain = OffsetChain()
        for line in buffer:
            chain.append(len(line) + 1)

        for index, elem in enumerate(chain.elements):
            line = index + 1
            byte = int(self.nvim.eval("line2byte(%i)" % line))
            self.nvim.command("echom 'Line %i\tByte: %i\tOffset: %i'" % (line, byte, elem.offset))

        tree = parser.parse(bytes("\n".join(buffer), "utf-8"))
        action = DelayedAction(0.1, lambda: self.nvim.async_call(lambda: show_tree(tree, self.nvim)))

        self.buffers[bufnr] = {
            'chain': chain,
            'tree': tree,
            'lines': list(buffer[::]),
            'action': action
        }

        action.reset()

    def update_buffer(self, bufnr, start, end, replacement):
        self.nvim.command("echom 'replacement: %s'" % str(replacement).replace("'", "''"))
        chain: OffsetChain = self.buffers[bufnr]['chain']
        tree: Tree = self.buffers[bufnr]['tree']
        lines: list = self.buffers[bufnr]['lines']


        start_byte = None
        start_point = None
        old_end_byte = None
        new_end_byte = None
        old_end_point = None
        new_end_point = None

        if start == end:
            # added
            start_byte = chain.elements[start] if start else 0
            start_point = (start, 0)
            old_end_byte = start_byte
            new_end_byte = start_byte + len(bytes("\n".join(replacement), "utf-8")) + 1
            old_end_point = start_point
            new_end_point = (start + len(replacement), 0)
            #TODO: insert all replacement lines into chain

        elif replacement:
            # replaced

            pass
        else:
            # deleted
            pass


        first_line = chain.elements[start]
        last_line = chain.elements[end]


        start_byte = first_line.offset + 1
        start_point = (start, 0)
        old_end_byte = last_line.offset + last_line.length + 1
        new_end_byte = start_byte + len(bytes("\n".join(replacement), "utf-8"))
        old_end_point = (end, last_line.length)
        new_end_point = (start - 1 + len(replacement), len(replacement[-1]) + 1) if replacement else start_point

        print("start_byte:", start_byte, "start_point:", start_point, "old_end_byte:", old_end_byte, "new_end_byte:", new_end_byte, "old_end_point:", old_end_point, "new_end_point:", new_end_point)

        tree.edit(
            start_byte = start_byte,
            old_end_byte = old_end_byte,
            new_end_byte = new_end_byte,
            start_point = start_point,
            old_end_point = old_end_point,
            new_end_point = new_end_point
        )

        for i in range(end, start, -1):
            del lines[i - 1]
        for i, line in enumerate(replacement):
            lines.insert(start + i, line)

        self.buffers[bufnr]['tree'] = parser.parse(bytes("\n".join(lines), "utf-8"))
        self.buffers[bufnr]['action'].reset()

        if replacement:
            chain.mass_update(ReplaceRangeOffsetChainUpdate(start, end, list(map(lambda l: len(l) + 1, replacement))))
        else:
            chain.mass_update(DeleteOffsetChainUpdate(list(range(start, end))))

    def handle_event(self, buffer, changedtick, firstline, lastline, linedata, is_multipart):
        if buffer not in self.buffers:
            self.parse_buffer(buffer)
        else:
            self.update_buffer(buffer, firstline, lastline, linedata)

    def detach(self, buffer):
        pass
