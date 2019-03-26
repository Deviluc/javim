from pynvim.plugin import plugin, command


from .maven import Maven
from .settings import RunConfiguration, PersistentSetting

__all__ = ["maven", "settings"]


class Javim():

    FIND_RESOURCES = 'find -L -type f -not \( -name "*.class" -or -name "*.java" -or -name "*.jar" \)'
    FIND_CLASSES = 'find -L -name "*.java"'

    FZF_FIND = ":nnoremap {map} :call fzf#run({'source': '{cmd} | sed ''s/^..//'', 'window': 'bot 10split enew', 'dir': '{dir}', 'sink': 'e'})"

    def __init__(self, vim):
        self.vim = vim
        self.maven = Maven(vim)
        self.buffers = {}
        cmd = Javim.FZF_FIND.replace("{dir}", self.maven.workspace.dir())
        class_cmd = cmd.replace("{cmd}", Javim.FIND_CLASSES).replace("{map}", "<leader>oc")
        resource_cmd = cmd.replace("{cmd}", Javim.FIND_RESOURCES).replace("{map}", "<leader>or")

        self.print("Class: " + class_cmd + "\nResource: " + resource_cmd)
        #vim.command(class_cmd)
        #vim.command(resource_cmd)

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


    def buf_delete(self, buf_num):
        if buf_num in self.buffers:
            del self.buffers[buf_num]

    def runAs(self, line_num, row_num):
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
        config = configs[choosen].create_config(line,
                                                row_num,
                                                source_file,
                                                project,
                                                self.maven)
        if not config:
            self.print("Couldn't create a run-configuration, retry manually!")

        maven_config = project['maven_config']

        if maven_config['rebuild']:
            self.maven.build_project(['clean', 'package', 'install'], project, maven_config['select_profiles'], maven_config['set_properties'])

        self.vim.command("bot new | call termopen('" + config.command().replace("'", "''") + "')")

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
        self.vim.command("autocmd! BufWritePost <buffer=" +
                         str(edit_buf.number) +
                         "> python3 javim.load_config(" +
                         project_name +
                         ", " + 
                         config_name + ")")

    def vim_quit(self):
        self.print("Saving javim settings...")
        PersistentSetting.save_all()
