""" Provides configuration objects persistent in the workspace """

from enum import Enum
from os import path, environ, mkdir, symlink, unlink
from os.path import join, exists, normpath, basename, expanduser
from shutil import rmtree
from subprocess import Popen
from json import dumps, loads
import atexit
import re

class PersistentSetting():
    """ Represents an object that is persistent across sessions """

    SETTINGS = []

    def __init__(self, directory, name, defaults, cleanup_func=None, on_load=None):
        self.path = path.join(directory, name) + ".json"
        self.__cleanup = cleanup_func
        if exists(self.path):
            with open(self.path, 'r') as f:
                self.data = loads(f.read())
        else:
            self.data = defaults

        for key in self.data:
            setattr(self,
                    "set_" + key,
                    (lambda k: lambda v: self.data.update({k: v}))(key))
            setattr(self, key, (lambda k: lambda: self.data[k])(key))

        PersistentSetting.SETTINGS.append(self)
        self.on_load = on_load


    def _save(self):
        if self.__cleanup:
            self.__cleanup(self.data)

        with open(self.path, 'w') as f:
            f.write(dumps(self.data, indent=4))

    def _load(self):
        with open(self.path, 'r') as f:
            self.data = loads(f.read())

        for key in self.data:
            setattr(self,
                    "set_" + key,
                    (lambda k: lambda v: self.data.update({k: v}))(key))
            setattr(self, key, (lambda k: lambda: self.data[k])(key))

        if self.on_load:
            self.on_load(self)


    @staticmethod
    def save_all():
        for setting in PersistentSetting.SETTINGS:
            setting._save()



class GlobalSetting(PersistentSetting):
    """ Represents an object that is persistent across sessions """

    if 'APPDATA' in environ:
        confighome = environ['APPDATA']
    elif 'XDG_CONFIG_HOME' in environ:
        confighome = environ['XDG_CONFIG_HOME']
    else:
        confighome = join(environ['HOME'], '.config')
    configpath = join(confighome, 'mavim')

    if not exists(configpath):
        mkdir(configpath)

    def __init__(self, name, defaults, cleanup_func = None):
        super(GlobalSetting, self).__init__(GlobalSetting.configpath,
                                            name,
                                            defaults,
                                            cleanup_func)


# pylint: disable=no-member
class Workspace(GlobalSetting):
    """ A workspace is a collection of projects """

    INSTANCE = None

    def __init__(self, name="Default workspace",
                 path_=path.join(expanduser('~'), 'javim-workspace')):

        super(Workspace, self).__init__("workspace_" + name.lower().replace(' ', '_'), {
            'name': name,
            'dir': path_,
            'settings_dir': join(path_, ".settings"),
            'projects': dict()
        }, self.__cleanup__)

        self.listeners = {
            'project_open': list(),
            'project_close': list()
        }

        if not path.exists(self.dir()):
            mkdir(self.dir())

        if not path.exists(self.settings_dir()):
            mkdir(self.settings_dir())

        def load_configs(provider):
            for project_name in self.projects():
                project = self.projects()[project_name]
                for config in project["run_config_names"].values():
                    if provider.name == config['provider_name']:
                        provider.load_config_func(config['config_name'], project)

        RunConfiguration.PROVIDER_REGISTER_HOOKS.append(load_configs)

        for project_name in self.projects():
            project = self.projects()[project_name]
            project['run_configs'] = {}
            for config in project['run_config_names'].values():
                if config['provider_name'] in RunConfiguration.PROVIDER:
                    RunConfiguration.PROVIDER[config['provider_name']].load_config_func(config['config_name'], project)
        Workspace.INSTANCE = self


    def __cleanup__(self, data):
        for project_name in data['projects']:
            del data['projects'][project_name]['run_configs']

    def import_project(self, name, directory):
        """ Adds a project to the workspace by creating a dynamic link """
        if name not in self.projects():
            dir_name = basename(normpath(directory))
            self.projects()[name] = {
                'name': name,
                'path': directory,
                'settings_dir': join(directory, ".settings"),
                'dir_name': dir_name,
                'open': True,
                'built': False,
                'run_config_names': {},
                'run_configs': {}}
            symlink(directory, join(self.dir(), dir_name))
            project = self.projects()[name]
            if not exists(project['settings_dir']):
                mkdir(project['settings_dir'])
                
            return project
        return None

    def add_project(self, name):
        """ Adds a project to the workspace. The directory must already
            exist """
        if name not in self.projects():
            self.projects()[name] = {'name': name,
                                     'path': join(self.dir(), name),
                                     'dir_name': name,
                                     'open': True,
                                     'built': False,
                                     'run_config_names': {},
                                     'run_configs': {}}
            project = self.projects()[name]
            project['settings_dir'] = join(project['path'], ".settings")

            if not exists(project['settings_dir']):
                mkdir(project['settings_dir'])

            return project
        return None

    def remove_project(self, name):
        """ Remove a project from the workspace """
        if name in self.projects():
            project = self.projects()[name]
            self.close_project(name)
            rmtree(project['settings_dir'])
            del self.projects[name]

    def get_project(self, name):
        """ Retrieves the project by name """
        if name in self.projects():
            return self.projects()[name]
        return None

    def close_project(self, project):
        """ Close the project """
        if project['open']:
            project['open'] = False
            unlink(join(self.dir(), project['dir_name']))
            for listener in self.listeners['project_close']:
                listener(project)

    def open_project(self, project):
        """ Open the project """
        if not project['open']:
            project['open'] = True
            symlink(self.dir(), project['dir_name'])
            for listener in self.listeners['project_open']:
                listener(project)


class ProjectSetting(PersistentSetting):
    """ Represents an object that is persistent across sessions in a """
    """specific project"""

    def __init__(self, name, project, defaults, cleanup_func=None, on_load=None):
        super(ProjectSetting, self).__init__(project['settings_dir'],
                                             name,
                                             defaults,
                                             cleanup_func=cleanup_func,
                                             on_load=on_load)


class RunConfigurationProvider():

    def __init__(self, name, mayrun_func, create_config_func, load_config_func):
        self.name = name
        self.mayrun = mayrun_func
        self.create_config = create_config_func
        self.load_config_func = load_config_func


class RunConfiguration(ProjectSetting):

    PROVIDER = {}
    PROVIDER_REGISTER_HOOKS = []

    @staticmethod
    def register_provider(provider):
        RunConfiguration.PROVIDER[provider.name] = provider
        for hook in RunConfiguration.PROVIDER_REGISTER_HOOKS:
            hook(provider)

    def __init__(self, name, project, command=None, debug_command=None, extra={}, provider=None, cleanup_func=None, on_load=None):
        super(RunConfiguration, self).__init__("run_configuration_" + name.lower().replace(' ', '_'),
                                               project,
                                               dict({'name': name,
                                                     'project_name': project['name'],
                                                     'command': command,
                                                     'debug_command': debug_command},
                                                    **extra),
                                               cleanup_func=cleanup_func,
                                               on_load=on_load)

        project['run_configs'][name] = self
        if name not in project['run_config_names'] and provider:
            project['run_config_names']["name"] = {'provider_name': provider.name,
                                                   'config_name': name}
    def update(self, maven):
        pass


class ProgramArgument:

    def __init__(self, name, description, template, possible_values=None):
        self.name = name
        self.description = description
        self.template = template
        self.possible_values = possible_values

    def build(self, value):
        return self.template.replace("{value}", str(value))


class JavaProgramArguments(Enum):

    CUSTOM_ARGUMENT = ProgramArgument("Custom argument", "", "{value}")


class JavaRunConfiguration(RunConfiguration):

    @staticmethod
    def filename_to_class(project, source_file):
        for source_dir in project['maven_config']['source_dirs']:
            if source_file.startswith(source_dir):
                main_class = source_file[len(source_dir) + 1:].replace("/", ".")
                main_class = main_class[:-len(".java")]
                return main_class
        return None


    @staticmethod
    def mayrun(line, col):
        return re.match(JavaRunConfiguration.MAIN_METH_REGEX, line.strip())


    @staticmethod
    def create_config(line, col, source_file, project, maven):
        main_class = JavaRunConfiguration.filename_to_class(project, source_file)
        return JavaRunConfiguration(main_class + "$main",
                                    project,
                                    main_class,
                                    {})

    @staticmethod
    def load_config(name, project):
        JavaRunConfiguration(name, project, None, None).rebuild_commands()

    MAIN_METH_REGEX = re.compile("(public|static)\\s+(static|public)\\s+void\\s+main\\s*\\(\\s*(final\\s+)?String\\[\\]\\s+\\w+\\s*\\)")
    BASE_COMMAND = "java -cp \"{classpath}\" {mainClass} {args}"
    DEBUG_COMMAND = "java -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address={port} -cp \"{classpath}\" {mainClass} {args}"

    RunConfiguration.register_provider(RunConfigurationProvider("Java Application",
                                                                mayrun.__func__,
                                                                create_config.__func__,
                                                                load_config.__func__))

    def __init__(self, name, project, main, args: dict = {}):
        super(JavaRunConfiguration, self).__init__(name,
                                                   project,
                                                   command="",
                                                   extra={'main_class': main,
                                                          'classpath': project['maven_config']['classpath'],
                                                          'args': args},
                                                   provider=RunConfiguration.PROVIDER["Java Application"],
                                                   on_load=lambda c: c.rebuild_commands())
        self.rebuild_commands()

    def rebuild_commands(self):
        project = Workspace.INSTANCE.projects()[self.project_name()]
        cp = project['maven_config']['classpath']
        main = self.main_class()
        arg_str = " ".join(arg.build(value) for arg, value in self.args().items())
        command = JavaRunConfiguration.BASE_COMMAND.replace("{classpath}", cp)
        command = command.replace("{mainClass}", main)
        command = command.replace("{args}", arg_str)

        debug_command = JavaRunConfiguration.DEBUG_COMMAND.replace("{classpath}", cp)
        debug_command = debug_command.replace("{mainClass}", main)
        debug_command = debug_command.replace("{args}", arg_str)

        self.set_command(command)
        self.set_debug_command(debug_command)

    def mayrun(self, line, col):
        return re.match is not None

    def update(self):
        self.rebuild_commands()
