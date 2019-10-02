from queue import Queue
from subprocess import run
from threading import Thread


class JobHandler:

    INSTANCES = []

    def __init__(self, vim):
        self.vim = vim
        self.jobs = {}
        self.processses = {}
        self.visible_running = False
        self.foreground_running = False
        self.waiting_jobs = Queue()
        JobHandler.INSTANCES.append(self)
        self.tid = 0

    def __check_queue(self, job_done):
        if job_done.fail_clear and job_done.failed:
            self.vim.command('echom "Job failed clearing queue..."')
            while not self.waiting_jobs.empty():
                self.waiting_jobs.get()
            return

        if not self.waiting_jobs.empty() and not self.visible_running or self.foreground_running:
            self.vim.command('echom "Job successfully, running next job..."')
            job = self.waiting_jobs.get()
            self.__start_job(job)
        else:
            self.vim.command('echom "No more jobs found!"')

    def __start_job(self, job):
        if job.options['visible']:
            buf_nr = int(self.vim.eval('bufnr("Console")'))
            if buf_nr != -1:
                self.vim.command("b %i | bw!" % buf_nr)
            self.vim.command("bot 10sp | enew")

            job_id = int(self.vim.eval(job.get_vim_command()))
            if job_id > 0:
                self.vim.command("file Console")
                self.visible_running = True
                self.jobs[job_id] = job
                self.vim.command("normal G")
            else:
                self.vim.command("bd!")
        elif job.options['foreground']:
            self.foreground_running = True
            self.vim.command("!%s" % job.cmd)
            self.foreground_running = False
            self.__check_queue()
        else:
            def run_thread(tid):
                self.subpress_exit(run(job.cmd,
                                       capture_output=True,
                                       encoding="utf-8",
                                       cwd=job.cwd))
            t = Thread(target=run_thread, args=self.tid)
            self.processses[self.tid] = job
            self.tid += 1
            t.start()

    def subpress_exit(self, process):
        args = process.args
        tid = None
        if type(args) == list:
            tid = args[0]
        else:
            tid = int(args)

        job = self.processses[tid]
        del self.processses[tid]
        self.foreground_running = False
        self.visible_running = False
        if process.return_code != 0:
            job.failed = True
        self.__check_queue(job)
        if job.on_exit:
            job.on_exit(JobResult(process.return_code,
                                  process.stdout,
                                  process.stderr))


    def handle_termclose(self, job_id, data):
        if job_id not in self.jobs:
            self.vim.command('echom "Job id %i unkown!"' % job_id)
            return
        job = self.jobs[job_id]
        del self.jobs[job_id]
        self.foreground_running = False
        self.visible_running = False
        if int(data) != 0:
            job.failed =True
        if job.on_exit:
            job.on_exit(JobResult(int(data), None, None))

        self.__check_queue(job)


    def start(self, job, visible=True, foreground=False):
        job.options['visible'] = visible
        job.options['foreground'] = foreground

        if visible:
            if self.visible_running or self.foreground_running:
                self.waiting_jobs.put(job)
            else:
                self.__start_job(job)
        elif foreground:
            if self.visible_running or self.foreground_running:
                self.waiting_jobs.put(job)
            else:
                self.__start_job(job)
        else:
            self.__start_job(job)


class Job:

    def __init__(self, job_type, cwd, cmd, on_exit=None, fail_clear=False):
        self.type = job_type
        self.cmd = cmd
        self.cwd = cwd
        self.on_exit = on_exit
        self.options = {}
        self.fail_clear = fail_clear
        self.failed = False

    def get_vim_command(self):
        return "termopen('" + self.cmd.replace("'", "''") + "', {'on_exit': 'javim#handleTermClose'})"


class JobResult:

    def __init__(self, return_code, stdout, stderr):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
