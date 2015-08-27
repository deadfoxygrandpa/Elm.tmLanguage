import collections
import webbrowser

from abc import abstractmethod
from datetime import datetime

try:     # ST3
    from .elm_plugin import *
    from .elm_project import ElmProject
except:  # ST2
    from elm_plugin import *
    from elm_project import ElmProject

default_exec = import_module('Default.exec')

class ElmPackageCommand(ElmBinCommandBase, default_exec.ExecCommand):
    class Args:
        env_key = 'build_env'
        package_key = 'elm_package'
        version_key = 'elm_package_version'

        def __init__(self, view):
            self.settings = view.settings()

        @property
        def package(self):
            env = self.settings.get(self.env_key, {})
            return env.get(self.package_key), env.get(self.version_key)

        @package.setter
        def package(self, value):
            name, version = value
            if name:
                env = {self.package_key: name or '', self.version_key: version}
                self.settings.set(self.env_key, env)
            else:
                self.settings.erase(self.env_key)

    def run(self, cmd, working_dir, **kwargs):
        project = ElmProject(cmd.pop())
        args = self.Args(self.window.active_view())
        package_name, version = args.package
        if package_name:
            cmd.append(package_name)
            if version:
                cmd.append(version)
            args.package = None, None
        project_dir = project.working_dir or working_dir
        super(ElmPackageCommand, self).run(cmd, working_dir=project_dir, **kwargs)

class ElmPackageCommandBase(abstract_class()):
    default_package_key = None

    Package = collections.namedtuple('Package', ['name', 'summary', 'versions'])

    def run(self, **kwargs):
        def on_fetch(json):
            default_package = self.Package(
                name=self.get_string(self.default_package_key),
                summary='',
                versions=None)
            decode_package = lambda json: self.Package(**json)
            self.packages = [default_package] + list(map(decode_package, json))
            self.show_packages()

        on_retry = lambda json: retry_on_main_thread(on_fetch, json)
        fetch_json(self.get_string('url.json'), on_retry)

    def get_string(self, key, *args, **kwargs):
        if 'use_prefix' not in kwargs:
            kwargs['use_prefix'] = False
        return get_string('package.' + key, *args, **kwargs)

    def show_packages(self):
        format_entry = lambda package: [package.name, package.summary]
        entries = list(map(format_entry, self.packages))
        on_select = lambda i: self.on_select(self.packages[i]) if i != -1 else None
        show_quick_panel(self.window, entries, on_select, on_highlight=self.on_highlight)

    @abstractmethod
    def on_select(self, package):
        pass

    def on_highlight(self, index):
        def on_fetch(json):
            if index == self.highlighted_index:
                stats = self.get_string('stats',
                    name=package.name,
                    version=package.versions[0],
                    date=datetime.strptime(json['pushed_at'], "%Y-%m-%dT%H:%M:%SZ"),
                    rating=self.calculate_rating(json),
                    use_prefix=True)
                sublime.status_message(stats)

        self.highlighted_index = index
        package = self.packages[index]
        if package.versions:
            fetch_json(self.get_string('url.repo', package.name), on_fetch)

    def calculate_rating(self, json):
        forks = json['forks_count']
        stars = json['stargazers_count']
        watchers = json['subscribers_count']
        return ((forks + 1) * (stars + 1) * (watchers + 1)) ** (1.0 / 3)

class ElmPackageInstallCommand(ElmPackageCommandBase, sublime_plugin.TextCommand):
    default_package_key = 'install.no_package'

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def run(self, edit, build_system):
        self.window = self.view.window()
        self.build_system = build_system
        self.default_version = self.get_string('install.no_version')
        super(ElmPackageInstallCommand, self).run()

    def on_select(self, package):
        if package.versions:
            versions = [self.default_version] + package.versions
            on_version = lambda i: self.on_version(package.name, versions[i]) if i != -1 else None
            show_quick_panel(self.window, versions, on_version)
        else:
            self.on_version(None, None)

    def on_version(self, package_name, version):
        self.window.run_command('set_build_system', dict(file=self.build_system))
        specific_version = version if version != self.default_version else None
        ElmPackageCommand.Args(self.view).package = package_name, specific_version
        self.window.run_command('build')

class ElmPackageOpenCommand(ElmPackageCommandBase, sublime_plugin.WindowCommand):
    default_package_key = 'open.no_package'

    def on_select(self, package):
        default_url = self.get_string('url.open_all')
        url = self.get_string('url.open', package.name) if package.versions else default_url
        webbrowser.open_new_tab(url)
