""" Provides configuration objects persistent in the workspace """


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

    def __init__(self, directory, name, defaults, cleanup_func=None):
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


    def __save(self):
        if self.__cleanup:
            self.__cleanup(self.data)

        with open(self.path, 'w') as f:
            f.write(dumps(self.data, indent=4))

    @staticmethod
    def save_all():
        for setting in PersistentSetting.SETTINGS:
            setting.__save()



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

        for project_name in self.projects():
            project = self.projects()[project_name]
            project['run_configs'] = {}
            for config_name in project['run_config_names']:
                RunConfiguration(config_name, project)


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
                'run_config_names': [],
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
                                     'run_config_names': [],
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

    def __init__(self, name, project, defaults, cleanup_func=None):
        super(ProjectSetting, self).__init__(project['settings_dir'],
                                             name,
                                             defaults,
                                             cleanup_func)


class RunConfigurationProvider():

    def __init__(self, name, mayrun_func, create_config_func):
        self.name = name
        self.mayrun = mayrun_func
        self.create_config = create_config_func



class RunConfiguration(ProjectSetting):

    PROVIDER = []

    def __init__(self, name, project, command=None, debug_command=None, extra={}):
        super(RunConfiguration, self).__init__("run_configuration_" + name.lower().replace(' ', '_'),
                                               project,
                                               dict({'name': name,
                                                     'project_name': project['name'],
                                                     'command': command,
                                                     'debug_command': debug_command},
                                                    **extra))

        project['run_configs'][name] = self
        if name not in project['run_config_names']:
            project['run_config_names'].append(name)


class JavaRunConfiguration(RunConfiguration):

    MAIN_METH_REGEX = re.compile("(public|static)\\s+(static|public)\\s+void\\s+main\\s*\\(\\s*(final\\s+)?String\\[\\]\\s+\\w+\\s*\\)")


    @staticmethod
    def mayrun(line, col):
        return re.match(JavaRunConfiguration.MAIN_METH_REGEX, line.strip())


    @staticmethod
    def create_config(line, col, source_file, project, maven):
        for source_dir in project['maven_config']['source_dirs']:
            if source_file.startswith(source_dir):
                main_class = source_file[len(source_dir) + 1:].replace("/", ".")
                main_class = main_class[:-len(".java")]
                return JavaRunConfiguration(main_class + "$main",
                                            project,
                                            main_class,
                                            maven.generate_classpath_entries(project),
                                            {})
        return None

    RunConfiguration.PROVIDER.append(RunConfigurationProvider("Java Application",
                                                              mayrun.__func__,
                                                              create_config.__func__))


    def __init__(self, name, project, main, cp_entries, args: dict = {}):
        command = ("java -cp \"" +
                   ":".join(cp_entries) +
                   "\" " +
                   main +
                   " " +
                   " ".join('"{0}"'.format(v) for v in args.values()))

        super(JavaRunConfiguration, self).__init__(name,
                                                   project,
                                                   command=command,
                                                   extra={'main_class': main,
                                                          'cp_entries': cp_entries,
                                                          'args': args})
    def mayrun(self, line, col):
        return re.match is not None


class UiTestRunConfiguration(JavaRunConfiguration):

    SETTINGS = GlobalSetting("ui-test", {'use_workspace_project': True})


    def __init__(self, name, project, testClass, testMethods, customer,
                 version):
        pass

