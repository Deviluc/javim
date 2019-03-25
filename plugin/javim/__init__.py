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
        vim.command(class_cmd)
        vim.command(resource_cmd)

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
        self.print("Executing command: " + config.command())
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


    def vim_quit(self):
        self.print("Saving javim settings...")
        PersistentSetting.save_all()
