from pynvim.plugin import plugin, command
from json import dumps, loads
import os
import tempfile


from .maven import Maven
from .settings import RunConfiguration, PersistentSetting
from .buffer_change import BufferChangeDispatcher
from .java import JavaAstBufferChangeListener

__all__ = ["maven", "settings"]


class Javim():

    FIND_RESOURCES = 'find -L -type f -not \\( -name "*.class" -or -name "*.java" -or -name "*.jar" -or -path "*/target/*" \\)'
    FIND_CLASSES = 'find -L -type f -name "*.java"'

    FZF_FIND = "nnoremap {map} :call fzf#run({'source': '{cmd} \\| sed \"s/^..//\"', 'window': 'bot 10split enew', 'dir': '{dir}', 'sink': 'e'})<CR>"

    NERDTREE_REFRESH_ROOT = "::NERDTreeRefreshRoot"


    def __init__(self, vim):
        self.vim = vim
        self.maven = Maven(vim)
        self.buffers = {}
        cmd = Javim.FZF_FIND.replace("{dir}", self.maven.workspace.dir())
        class_cmd = cmd.replace("{cmd}", Javim.FIND_CLASSES).replace("{map}", "<leader>oc")
        resource_cmd = cmd.replace("{cmd}", Javim.FIND_RESOURCES).replace("{map}", "<leader>or")
        vim.command(class_cmd)
        vim.command(resource_cmd)
        self.last_config = None

        self.debug_port = 8100
        self.event_listeners = {}
        self.listen_path = vim.command_output(":let a = systemlist('echo $NVIM_LISTEN_ADDRESS')|echo a[0]")
        #self.change_dispatcher = BufferChangeDispatcher(self.vim, True)
        #self.java_ast = JavaAstBufferChangeListener(self.vim)
        #self.change_dispatcher.register_filetype_listener(self.java_ast, [".java"])


    def __handle_event(self, name, event):
        if name in self.event_listeners:
            for listener in self.event_listeners:
                listener(*event)


    def print(self, msg):
        self.vim.command("echom \"" + str(msg).replace("\"", "\\\"") + "\"")

    def input(self, message):
        self.vim.command('call inputsave()')
        self.vim.command("let user_input = input('" + message + ": ')")
        self.vim.command('call inputrestore()')

        return self.vim.eval('user_input')

    def choice(self, choices):
        self.vim.command("call inputsave()")
        self.vim.command("let user_input = inputlist([" + ", ".join(map(lambda c: "'" + c + "'", choices)) + "])")
        self.vim.command("call inputrestore()")
        
        return int(self.vim.eval("user_input"))

    def get_choice(self, choices):
        result = self.choice(choices)
        return choices[result]

    def buf_enter(self, buf_num):
        buff = self.vim.buffers[buf_num]

        if "project_name" not in buff.vars:
            if buff.valid and buff.name:
                file_name = buff.name
                for project_name, project in self.maven.workspace.projects().items():
                    if file_name.startswith(project['path']):
                        buff.vars['project_name'] = project_name
                        self.buffers[buf_num] = {'project_name': project_name}
                        return

    def find_project_by_buffer(self, buf_num):
        buff = self.vim.buffers[buf_num]

        if "project_name" not in buff.vars:
            if buff.valid and buff.name:
                file_name = buff.name
                for project_name, project in self.maven.workspace.projects().items():
                    if file_name.startswith(project['path']):
                        buff.vars['project_name'] = project_name
                        self.buffers[buf_num] = {'project_name': project_name}
                        return project
        else:
            return self.maven.workspace.projects()[buff.vars["project_name"]]


    def buf_delete(self, buf_num):
        if buf_num in self.buffers:
            del self.buffers[buf_num]

    def buf_save(self, buf_num):
        buff = self.vim.buffers[buf_num]
        if "project_name" in buff.vars:
            project = self.maven.workspace.projects()[buff.vars['project_name']]
            project['maven_config']['rebuild'] = True

    def __run_config(self, config, is_debug=False):
        buf_nr = int(self.vim.eval('bufnr("Console")'))
        if buf_nr != -1:
            self.vim.command("b %i | bw!" % buf_nr)
        command = config.command() if not is_debug else config.debug_command()
        if is_debug:
            command = command.replace("{port}", str(self.debug_port))
        self.print("Running command: " + command)
        self.vim.command("bot 10sp | enew | call termopen('" + command.replace("'", "''") + "')")
        self.vim.command("file Console")
        self.vim.command("normal G")

        if is_debug:
            self.vim.command("call vebugger#jdb#attach('" + str(self.debug_port) + "', {'srcpath':" + str(config.src()) + "})")
            self.debug_port += 1

        self.last_config = config

    def runAs(self, line_num, row_num, is_debug=False):
        line = self.vim.eval('getline(' + str(line_num) + ')')
        names = []
        configs = []
        for i, (name, configProvider) in enumerate(RunConfiguration.PROVIDER.items()):
            if configProvider.mayrun(line, row_num):
                names.append(str(i) + ": " + configProvider.name)
                configs.append(configProvider)

        if not names:
            self.print("No matching run-configurations found!")
            return
        choosen = self.choice(names)
        if choosen >= len(names):
            self.print("Invalid choice!")
            return

        buff = self.vim.current.buffer
        source_file = buff.name
        project = self.maven.workspace.projects()[buff.vars['project_name']]
        def run_config():
            buf_nr = int(self.vim.eval('bufnr("Console")'))
            if buf_nr != -1:
                self.vim.command("b %i | bw!" % buf_nr)
            config = configs[choosen].create_config(line,
                                                    row_num,
                                                    source_file,
                                                    project,
                                                    self.maven)
            if not config:
                self.print("Couldn't create a run-configuration, retry manually!")

            self.__run_config(config, is_debug)

        self.maven.build_project_and_dependencies(project, run_config)

    def run_last(self, is_debug=False):
        if self.last_config:
            self.__run_config(self.last_config, is_debug)


    def get_project(self, name):
        if name in self.maven.workspace.projects():
            return self.maven.workspace.projects()[name]

        self.print("No project '" + name + "' in the workspace!")
        return None

    def select_profile(self, project, profile):
        config = project['maven_config']
        if profile in config['profiles']:
            if profile not in config['select_profiles']:
                config['select_profiles'].append(profile)
            return
        self.print("No profile '" + profile + "' in project '" + project['name'] + "'!")

    def deselect_profile(self, project, profile):
        config = project['maven_config']
        if profile in config['select_profiles']:
            config['select_profiles'].remove(profile)

    def set_profiles(self, profiles):
        buf = self.vim.current.buffer
        if 'project_name' not in buf.vars:
            self.print("This file doesn't belong to a managed project!")
            return

        project = self.maven.workspace.projects()[buf.vars['project_name']]
        maven_config = project['maven_config']
        maven_config['select_profiles'] = []
        for profile in profiles.split(","):
            maven_config['selected_profiles'].append(profile)
        maven_config['rebuild'] = True

            
    def set_selected_profiles(self, project, profiles):
        config = project['maven_config']

        for profile in profiles:
            if profile not in config['profiles']:
                self.print("No profile '" + profile + "' in project '"
                           + project['name'] + "'!")
                return

        config['select_profiles'] = profiles


    def project_import(self, project_path):
        self.print("Importing maven project at '" + project_path + "'...")
        project = self.maven.import_project(project_path)
        if project:
            self.print("Successfully import project '" + project['name'] + "'!")
        else:
            self.print("Project couldn't be imported!")

    def select_project(self):
        projects = [project['name'] for project in self.maven.workspace.projects()]
        return self.maven.workspace.projects()[self.get_choice(projects)]

    def project_close(self):
        self.maven.workspace.close_project(self.select_project())

    def project_open(self):
        self.maven.workspace.open_project(self.select_project())


    def load_config(self, project_name, config_name):
        if project_name not in self.maven.workspace.projects():
            self.print("No project with name '" + project_name + "'!")
            return

        project = self.maven.workspace.projects()[project_name]

        if config_name not in project['run_configs']:
            self.print("Project '" + project_name + "' has not run-configuration with name '" + config_name + "'!")
            return
        
        config = project['run_configs'][config_name]
        config._load()


    def edit_run_configurations(self):
        buff = self.vim.current.buffer
        if not 'project_name' in buff.vars:
            self.print("Not a managed project file!")
            return

        project_name = buff.vars['project_name']
        project = self.maven.workspace.projects()[project_name]

        if not len(project['run_configs']):
            self.print("No run-configurations for project '" + project_name + "'!")
            return

        config_name = self.get_choice(list(project['run_configs'].keys()))
        config = project['run_configs'][config_name]
        config._save()
        self.vim.command("e " + config.path.replace("$", "\\$"))
        edit_buf = self.vim.current.buffer
        autocmd = "au! BufWritePost <buffer=%i> python3 javim.load_config(\"%s\", \"%s\")" % (edit_buf.number,
                                                                                              project_name,
                                                                                              config_name)
        self.vim.command(autocmd)



    def edit_project_configuration(self):
        buff = self.vim.current.buffer
        if not 'project_name' in buff.vars:
            self.print("Not a managed project file!")
            return

        project_name = buff.vars['project_name']
        project = self.maven.workspace.projects()[project_name]

        _, tmp_name = tempfile.mkstemp(suffix=".json")

        self.vim.command("enew")
        self.vim.command("e %s" % tmp_name)
        buffer = self.vim.current.buffer

        run_configs = project['run_configs']
        project['run_configs'] = {}
        project_config = dumps(project, indent=4)
        project['run_configs'] = run_configs
        buffer[::] = project_config.split("\n")

        bufnr = buffer.number
        autocmd = "au! BufWriteCmd <buffer=%i> python3 javim.save_project_config(%i, '%s')" % (bufnr, bufnr, project_name)
        self.vim.command(autocmd)
        self.vim.command("au! BufDelete <buffer=%i> python3 os.remove('%s')" % (bufnr, tmp_name))

    def save_project_config(self, bufnr, project_name):
        workspace = self.maven.workspace
        old_project = workspace.projects()[project_name]
        buff = self.vim.buffers[bufnr]

        try:
            project = loads("\n".join(buff))
            project['run_configs'] = old_project['run_configs']
            workspace.projects()[project_name] = project
            workspace._save()
            self.vim.command("echom 'Project configuration saved successfully!'")
        except Exception as e:
            workspace.projects()[project_name] = old_project
            workspace._save()
            self.vim.command("echom 'Error saving project config: %s'" % str(e))

    def vim_quit(self):
        self.print("Saving javim settings...")
        PersistentSetting.save_all()
