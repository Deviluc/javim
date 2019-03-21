""" This module provides the means to compile, run and manage workspace
    projects with maven"""
from os import mkdir, remove
from os.path import exists, join, basename, normpath, expanduser
from subprocess import run
import time
from lxml import etree
from .settings import Workspace, GlobalSetting


class Maven():
    """ Represents the interface to communicate with maven """
    COMMAND_TEMPLATE = "!%s %s"
    COMMAND_DIR_TEMPLATE = "!%s -f %s/pom.xml %s"
    COMMAND_CHDIR_TEMPLATE = "!cd %s && %s %s"
    CREATION_TEMPLATE = ("archetype:generate -DgroupId=%s -DartifactId=%s "
                         "-DarchetypeArtifactId=%s -DarchetypeVersion=%s "
                         "-DinteractiveMode=false")
    PROPERTIES_TEMPLATE = "-D%s=%s"
    PROFILES_TEMPLATE = "-P%s"
    BUILD_TEMPLATE = "!%s -f %s %s %s %s" 
    GEN_POM_TEMPLATE = "%s help:effective-pom %s"
    DEP_KEY_TEMPLATE = "%s:%s:%s"
    LOCAL_REPO_TEMPLATE = ("%s help:evaluate -Dexpression="
                           "settings.localRepository -Doutput=%s")

    GROUPID_XPATH = "//ns:project/ns:groupId/text()"
    ARTIFACTID_XPATH = "//ns:project/ns:artifactId/text()"
    VERSION_XPATH = "//ns:project/ns:version/text()"
    NAME_XPATH = "//ns:project/ns:name/text()"
    DESCRIPTION_XPATH = "//ns:project/ns:name/text()"
    URL_XPATH = "//ns:project/ns:url/text()"

    PROFILES_XPATH = "//ns:profile/ns:id/text()"
    PROPERTIES_XPATH = "//ns:properties/*"
    SOURCE_DIR_XPATH = "//ns:build/ns:sourceDirectory/text()"
    TEST_SOURCE_DIR_XPATH = "//ns:build/ns:testSourceDirectory/text()"
    OUTPUT_DIR_XPATH = "//ns:build/ns:outputDirectory/text()"
    TEST_OUTPUT_DIR_XPATH = "//ns:build/ns:testOutputDirectory/text()"
    RESOURCE_DIRS_XPATH = ("//ns:build/ns:resources/ns:resource/ns:directory"
                           "/text()")
    TEST_RESOURCE_DIRS_XPATH = ("//ns:build/ns:testResources/ns:testResource"
                                "/directory/text()")

    DEPENDENCY_XPATH = "//ns:project/ns:dependencies/ns:dependency"
    DEP_GROUPID_XPATH = "ns:groupId/text()"
    DEP_ARTIFACTID_XPATH = "ns:artifactId/text()"
    DEP_VERSION_XPATH = "ns:version/text()"
    DEP_SCOPE_XPATH = "ns:scope/text()"

    SETTINGS = GlobalSetting("maven",
                             {'executable': 'mvn',
                              'repo_path': expanduser('~/.m2/repository'),
                              'default_java_source': '1.8',
                              'default_java_target': '1.8'})

    INSTANCE = None

    def __init__(self, vim, workspace=Workspace()):
        self.workspace = workspace
        self.vim = vim
        self.project_config = dict()
        self.executable = Maven.SETTINGS.executable()
        vim.command("cd " + self.workspace.dir())
        Maven.INSTANCE = self

    def __print_error(self, msg):
        self.vim.command("echoerr \"%s\"" % msg)

    def __print(self, msg):
        self.vim.command("echo \"%s\"" % (msg.replace("\n", "\\n")))


    def init_project_config(self, project):
        """ Creates the initial project configuration with default values """
        project['maven_config'] = {'profiles': [],
                                   'selected_profiles': [],
                                   'properties': {},
                                   'set_propreties': {},
                                   'source_dirs': [],
                                   'test_source_dirs': [],
                                   'resource_dirs': [],
                                   'test_resource_dirs': [],
                                   'output_dir': "target/classes",
                                   'test_output_dir': "target/test-classes",
                                   'dependencies': [],
                                   'dep_classpath': [],
                                   'dep_projects': [],
                                   'last_built': None}

        project['maven_info'] = {'groupId': '',
                                 'artifactId': '',
                                 'version': '',
                                 'name': '',
                                 'description': '',
                                 'url': ''}

        if "java_config" not in project:
            project['java_config'] = {}

        java_config = project['java_config']

        if "source" not in java_config:
            java_config['source'] = Maven.SETTINGS.default_java_source()
        if "target" not in java_config:
            java_config['target'] = Maven.SETTINGS.default_java_target()

    # pylint: disable=R0913
    def create_project(self, group_id, artifact_id, name=None,
                       archetype="maven-archetype-simple", version="1.4",
                       target_dir=None):
        """ Creates a new maven project, default archetype is the most simple.
            A target directory can be supplied, that directory shouldn't be in
            the workspace.
            The supplied name will determine the name of the link """

        if not target_dir:
            proj_name = name if name else artifact_id
            proj_path = join(self.workspace.dir(), proj_name)
            if not exists(proj_path):
                mkdir(proj_path)
        else:
            proj_name = basename(normpath(target_dir))
            proj_path = normpath(target_dir)

        if proj_name in self.workspace.projects():
            self.__print_error(("There is already a project with name '%s' in "
                                "the current workspace") % proj_name)
            return None

        mvn_command = Maven.CREATION_TEMPLATE % (group_id, artifact_id,
                                                 archetype, version)

        self.vim.command(Maven.COMMAND_CHDIR_TEMPLATE % (proj_path,
                                                         self.executable,
                                                         mvn_command))
        project = self.workspace.add_project(proj_name)
        self.init_project_config(project)
        eff_pom = self.create_effective_pom(project)

        if not eff_pom:
            self.__print_error("Error importing project!")
            self.workspace.remove_project(project['name'])
            return None

        self.process_pom(project, eff_pom)
        self.process_added_project(project)

        return project

    def import_project(self, directory, name=None):
        """ Import an existing maven project into the workspace, the name
            must be unique. If none is provided, one must be set in the
            imported projects pom.xml """
        pom_path = join(directory, "pom.xml")
        if not exists(pom_path):
            self.__print_error("Couldn't find pom.xml in '" + pom_path + "'!")

        pom, namespace = self.read_pom(None, pom_path)
        if not pom:
            return None

        name = name if name else self.xpath(pom, Maven.NAME_XPATH, namespace)[0]
        if name in self.workspace.projects():
            self.__print_error(("There is already a project with name '%s' in "
                                "the current workspace!") % name)
            return None

        project = self.workspace.import_project(name, directory)
        self.init_project_config(project)
        eff_pom = self.create_effective_pom(project)
        if not eff_pom:
            self.workspace.remove_project(project['name'])
            return None

        self.process_pom(project, eff_pom)
        self.process_added_project(project)
        
        return project

    def build_project(self, goals, project, profiles=None, properties=None):
        """ Builds the projects using the provided goals """

        goals_ = " ".join(goals)
        profiles_ = ",".join(profiles or [])
        if profiles:
            profiles_ = Maven.PROFILES_TEMPLATE % profiles_
        props = " ".join(map(lambda k: Maven.PROPERTIES_TEMPLATE
                             % (k, properties[k]), properties or []))

        self.vim.command(Maven.BUILD_TEMPLATE % (self.executable(),
                                                 project['path'],
                                                 goals_,
                                                 profiles_,
                                                 props))
        project['maven_config']['last_built'] = time.time()

    def read_xml_with_namespace(self, path):
        """ Reads the file from path into an xml-tree and extracts the """
        """ namespace"""
        try:
            tree = etree.parse(path)
            root = tree.getroot()
            namespace = root.nsmap[root.prefix]
            return (tree, namespace)
        except Exception as e:
            self.__print_error("Cannot read '" + path + "': " + str(e))
            return None

    def read_pom(self, project, pom_path=None):
        """ Reads the pom.xml into a tree object """
        path = pom_path if pom_path else join(project['path'], 'pom.xml')
        return self.read_xml_with_namespace(path)

    def xpath(self, node, path, namespace):
        """" Evaluates an xpath expression using the provided namespace """
        return node.xpath(path, namespaces={'ns': namespace})

    def create_effective_pom(self, project):
        """ Create the effective pom and parse as xml tree """
        profiles = project['maven_config']['profiles']
        prof_str = ",".join(profiles)
        if prof_str:
            prof_str = Maven.PROFILES_TEMPLATE % prof_str

        tmp_pom_path = join(self.workspace.dir(), "." + project['name'] +
                            ".pom.xml")
        args = [self.executable, "-Doutput=" + tmp_pom_path, "help:effective-pom"]
        if prof_str:
            args.append(prof_str)

        res = run(args,
                  capture_output=True,
                  encoding="utf-8",
                  cwd=project['path'])
        if res.returncode:
            self.__print_error("Error generating effective pom.xml\n" + res.stdout)
            return None

        try:
            tree = etree.parse(open(tmp_pom_path, 'r'))
            remove(tmp_pom_path)
            return tree
        except Exception as e:
            self.__print_error("Error parsing effective pom:\n" + str(e))
            return None

    def process_pom(self, project, pom_tree):
        """ Parse pom and apply config to project """
        root = pom_tree.getroot()
        namespace = root.nsmap[root.prefix]

        def tree_xpath(path):
            return self.xpath(pom_tree, path, namespace)

        def xpath(node, path):
            return self.xpath(node, path, namespace)

        info = project['maven_info']
        info['groupId'] = tree_xpath(Maven.GROUPID_XPATH)[0]
        info['artifactId'] = tree_xpath(Maven.ARTIFACTID_XPATH)[0]
        info['version'] = tree_xpath(Maven.VERSION_XPATH)[0]
        name_elem = tree_xpath(Maven.NAME_XPATH)
        info['name'] = name_elem[0] if name_elem else None
        desc_elem = tree_xpath(Maven.DESCRIPTION_XPATH)
        info['description'] = desc_elem[0] if desc_elem else None
        url_elem = tree_xpath(Maven.URL_XPATH)
        info['url'] = url_elem[0] if url_elem else None

        config = project['maven_config']
        config['profiles'] = tree_xpath(Maven.PROFILES_XPATH)

        for prop in tree_xpath(Maven.PROPERTIES_XPATH):
            key = prop.tag
            if key[0] == '{':
                key = key[len(namespace) + 2:]

            val = prop.text
            config['properties'][key] = val

        config['source_dirs'] = tree_xpath(Maven.SOURCE_DIR_XPATH)
        config['test_source_dirs'] = tree_xpath(Maven.TEST_SOURCE_DIR_XPATH)
        config['output_dir'] = tree_xpath(Maven.OUTPUT_DIR_XPATH)[0]
        config['test_output_dir'] = tree_xpath(Maven.TEST_OUTPUT_DIR_XPATH)[0]
        config['resource_dirs'] = tree_xpath(Maven.RESOURCE_DIRS_XPATH)
        config['test_resource_dirs'] = tree_xpath(Maven.TEST_RESOURCE_DIRS_XPATH)
        config['dependencies'] = {}

        for _dep in tree_xpath(Maven.DEPENDENCY_XPATH):
            dep = {
                    'groupId': xpath(_dep, Maven.DEP_GROUPID_XPATH)[0],
                    'artifactId': xpath(_dep, Maven.DEP_ARTIFACTID_XPATH)[0],
                    'version': xpath(_dep, Maven.DEP_VERSION_XPATH)[0],
                    'scope': xpath(_dep, Maven.DEP_SCOPE_XPATH)[0]
                  }
            config['dependencies'][Maven.DEP_KEY_TEMPLATE
                                   % (dep['groupId'],
                                      dep['artifactId'],
                                      dep['version'])] = dep

    def generate_classpath_entries(self, project):
        """ Generates a list of entries to add to the classpath in order to """
        """ run the provided project """
        config = project['maven_config']
        entries = []
        base = Maven.SETTINGS.repo_path()

        skipdeps = []
        
        for proj in map(self.workspace.get_project, config['dep_projects']):
            if proj['open']:
                entries.append(proj['maven_config']['output_dir'])
                info = proj['maven_info']
                depkey = Maven.DEP_KEY_TEMPLATE % (info['groupId'],
                                                   info['artifact'],
                                                   info['version'])
                skipdeps.append(depkey)

        for depkey, dep in config['dependencies'].items():
            if depkey in skipdeps:
                continue

            path = join(base,
                        dep['groupId'].replace(".", "/"),
                        dep['artifactId'],
                        dep['version'],
                        dep['artifactId'] + "-" + dep['version'] + '.jar')
            entries.append(path)

        entries.append(config['output_dir'])

        return entries

    def process_added_project(self, project):
        """ Should be called when a new maven project was added to update """
        """ workspace dependencies """
        info = project['maven_info']
        config = project['maven_config']
        name = project['name']
        project_dep_key = Maven.DEP_KEY_TEMPLATE % (info['groupId'],
                                                    info['artifactId'],
                                                    info['version'])
        for proj in self.workspace.projects():
            if proj is not project and 'maven_info' in proj:
                info_ = proj['maven_info']
                config_ = proj['maven_config']
                name_ = proj['name']
                proj_dep_key = Maven.DEP_KEY_TEMPLATE % (info_['groupdId'],
                                                         info_['artifactId'],
                                                         info_['version'])

                if (project_dep_key in config_['dependencies'] and
                   name not in config_['dep_projects']):
                    config_['dep_projects'].append(name)

                if (proj_dep_key in config['dependencies']
                   and name_ not in config['dep_projects']):
                    config['dep_projects'].append(name_)

    def build_workspace(self):
        """ Build every maven project in the workspace """
        for project in self.workspace.projects():
            if 'maven_config' in project:
                config = project['maven_config']
                self.build_project(["compile"],
                                   project,
                                   config['selected_profiles'],
                                   config['set_properties'])
















