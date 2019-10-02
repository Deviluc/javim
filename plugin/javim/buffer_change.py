from neovim import attach
from pynvim.api.buffer import Buffer
from multiprocessing import Process, SimpleQueue, set_start_method
from threading import Thread
from enum import Enum, auto
import re
import tempfile
from os import path
import asyncio
from time import sleep

class BufferSelectionType(Enum):
    ANY = auto()
    FIXED = auto()
    FILETYPE = auto()
    REGEX = auto()


def buffer_change_dispatcher_process(rpc_path, queue, buf_queue):
    nvim = attach("socket", path=rpc_path)

    def echom(msg):
        nvim.command("echom '%s'" % msg.replace("'", "''"))

    echom("Connected to neovim!")

    for buffer in nvim.buffers:
        #echom("Attaching to buffer: %i" % buffer.number)
        nvim.api.buf_attach(buffer.number, False, {})

    def thread_loop(queue):
        buf = queue.get()
        while buf:
            nvim.async_call(lambda: nvim.api.buf_attach(buf, False, {}))
            buf = queue.get()
    thread = Thread(target=thread_loop, args=(buf_queue,))
    thread.start()

    def process_request(*args):
        echom("Request: %s" % str(args))
    def process_notification(*args):
        name, a = args
        if name in ['nvim_buf_lines_event', 'nvim_buf_detach_event']:
            a = [r.number if type(r) == Buffer else r for r in a]
            #echom("Notification: %s" % str(a))
            queue.put((name, a))
    def process_error(*args):
        echom("Error: %s" % str(args))

    #echom("Starting event loop...")
    nvim.run_loop(process_request, process_notification)
    queue.put(False)
    buf_queue.put(False)
    thread.join()
    #echom("Terminated event loop!")


class BufferChangeDispatcher:

    INSTANCE = None
    _PROCESS_INSTANCE = None

    def __init__(self, vim, debug = False):
        if BufferChangeDispatcher.INSTANCE is not None:
            raise RuntimeError("Only one instance of BufferChangeDispatcher is allowed!")

        BufferChangeDispatcher.INSTANCE = self

        d = tempfile.mkdtemp()
        self.rpc_path = path.join(d, "bufferChangeDispatcher")

        vim.command("call serverstart('%s')" % self.rpc_path)
        print("Started server at: %s" % self.rpc_path)

        self.listeners = {
            BufferSelectionType.ANY: list(),
            BufferSelectionType.FIXED: list(),
            BufferSelectionType.FILETYPE: list(),
            BufferSelectionType.REGEX: list()
        }

        if debug:
            def lis_func(buffer, changedtick, firstline, lastline, linedata, is_multipart):
                print("###\tCHANGE_EVENT\t###")
                print("Buffer:", buffer)
                print("ChangedTick:", changedtick)
                print("Firstline:", firstline)
                print("Lastline:", lastline)
                print("Linedata:", linedata)
                print("Multipart:", is_multipart, end="\n\n")
            def detach_func(buffer):
                print("###\tDETACH_EVENT\t###")
                print("Detached from buffer:", buffer, end="\n\n")

            debug_listener = BufferChangeListener("debug_listener", listener_func=lis_func, detach_func=detach_func)
            self.register_listener(debug_listener)

        self.nvim = vim
        queue = SimpleQueue()
        self.buf_queue = SimpleQueue()
        self.process = Process(target=buffer_change_dispatcher_process, args=(self.rpc_path, queue, self.buf_queue))
        self.process.start()
        self.nvim.command("py3 from javim.buffer_change import BufferChangeDispatcher")
        self.nvim.command("autocmd! BufAdd * py3 BufferChangeDispatcher.INSTANCE.buf_queue.put(int(vim.eval(\"expand('<abuf>')\")))")

        def thread_loop(queue):
            obj = queue.get()
            while obj:
                self.nvim.async_call(lambda: self.nvim.command("echom 'Got event: %s'" % str(obj).replace("'", "''")))
                name, args = obj
                self.nvim.async_call(lambda: self.__handle_event__(name, args))
                obj = queue.get()
            self.nvim.command("echom 'Terminated thread loop!'")
            self.process.join()

        self.thread = Thread(target=thread_loop, args=(queue,))
        self.thread.start()

    def __matches_listener(self, selection_type, bufnr, listener):
        buffer = self.nvim.buffers[bufnr]

        if selection_type == BufferSelectionType.ANY:
            return (True, listener)
        elif selection_type == BufferSelectionType.FIXED:
            buffers, lis = listener
            return (buffer.number in buffers, lis)
        elif selection_type == BufferSelectionType.FILETYPE:
            filetypes, lis = listener
            for filetype in filetypes:
                if buffer.name.endswith(filetype):
                    return (True, lis)
        elif selection_type == BufferSelectionType.REGEX:
            regex, lis = listener
            return (re.match(regex, buffer.name), lis)
        return (False, None)

    def __handle_event__(self, event_name, args):
        if event_name == "nvim_buf_lines_event":
            for selection_type in BufferSelectionType:
                for listener in map(lambda l: l[1], filter(lambda l: l[0], map(lambda l: self.__matches_listener(selection_type, args[0], l), self.listeners[selection_type]))):
                    listener.handle_event(*args)


        elif event_name == "nvim_buf_detach_event":
            for selection_type in BufferSelectionType:
                for listener in map(lambda l: l[1], filter(lambda l: l[0], map(lambda l: self.__matches_listener(selection_type, args[0], l), self.listeners[selection_type]))):
                    listener.detach(*args)

    def register_listener(self, listener):
        self.listeners[BufferSelectionType.ANY].append(listener)

    def register_fixed_listener(self, listener, buffers):
        self.listeners[BufferSelectionType.FIXED].append((buffers, listener))

    def register_filetype_listener(self, listener, filetypes):
        self.listeners[BufferSelectionType.FILETYPE].append((filetypes, listener))

    def register_regex_listener(self, listener, regex):
        self.listeners[BufferSelectionType.REGEX].append((regex, listener))


class BufferChangeListener:
    """
    A BufferChangeListener is notified on each change on the
    specified (or all) buffers
    """

    def __init__(self, name, listener_func=None, detach_func=None):
        """
        Creates a new BufferChangeListener

        [name]: unique name to identify this BufferChangeListener

        [listener_func]: see BufferChangeListener.handle_event

        [detach_func]: see BufferChangeListener.detach
        """
        self.name = name
        self.func = listener_func
        self.detach_func = detach_func if detach_func else lambda b: None

    def handle_event(self, buffer, changedtick, firstline, lastline, linedata, is_multipart):
        """ 
        A BufferChangeListener must implent this method or pass it to
        the constructor (listener_func). It will be called on each buffer change.

        [buffer]: buffer object

        [changedtick]: value of |b:changedtick| for the buffer. If you send an API
        command back to nvim you can check the value of |b:changedtick| as part of
        your request to ensure that no other changes have been made.

        [firstline]: integer line number of the first line that was replaced.
        Zero-indexed: if line 1 was replaced then [firstline] will be 0, not 1.
        [firstline] is always less than or equal to the number of lines that were
        in the buffer before the lines were replaced.

        [lastline]: integer line number of the first line that was not replaced
        (i.e. the range firstline, lastline is end-exclusive).
        Zero-indexed: if line numbers 2 to 5 were replaced, this will be 5 instead
        of 6. lastline is always be less than or equal to the number of lines
        that were in the buffer before the lines were replaced. lastline will be
        -1 if the event is part of the initial update after attaching.

        [linedata]: list of strings containing the contents of the new buffer
        lines. Newline characters are omitted; empty lines are sent as empty
        strings.

        [is_multipart]: boolean, true for a "multipart" change notification: the current
        change was chunked into multiple |nvim_buf_lines_event| notifications
        (e.g. because it was too big).
        """
        self.func(buffer, changedtick, firstline, lastline, linedata, is_multipart)

    def detach(self, buffer):
        """ 
        A BufferChangeListener should implent this method or pass it to 
        the constructor (detach_func) when a function should be
        executed when a buffer is not watched anymore.

        When buffer is detached (i.e. updates are disabled). Triggered explicitly by
        nvim_buf_detach() or implicitly in these cases:
        - Buffer was abandoned and 'hidden' is not set.
        - Buffer was reloaded, e.g. with :edit or an external change triggered
          :checktime or 'autoread'.
        - Generally: whenever the buffer contents are unloaded from memory.

        [buffer]: buffer object
        """
        if self.detach_func:
            self.detach_func(buffer)

    def __eq__(self, other):
        if type(other) ==  BufferChangeListener:
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)
