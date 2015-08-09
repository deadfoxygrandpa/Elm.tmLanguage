try:     # ST3
    from .elm_plugin import *
    from .elm_project import ElmProject
except:  # ST2
    from elm_plugin import *
    from elm_project import ElmProject

class ElmOpenInBrowserCommand(sublime_plugin.TextCommand):

    @staticmethod
    def _import_bases():
        return __import__('SideBarEnhancements').SideBar.SideBarOpenInBrowserCommand,

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def run(self, edit):
        norm_path = fs.join(self.project.working_dir, fs.expanduser(self.project.html_path))
        html_path = fs.abspath(norm_path)
        if not fs.isfile(html_path):
            sublime.status_message(get_string('open_in_browser.not_found', html_path))
            return
        try:
            self._import_bases()
        except ImportError:
            log_string('logging.missing_plugin', 'SideBarEnhancements')
            if ElmViewInBrowserProxyCommand.is_patched:
                self.view.run_command('elm_view_in_browser_proxy', dict(path=html_path))
            else:
                sublime.status_message(get_string('open_in_browser.missing_plugin'))
        else:
            self.view.window().run_command('side_bar_open_in_browser', dict(paths=[html_path]))

class ElmViewInBrowserProxyCommand(sublime_plugin.TextCommand):

    @staticmethod
    def _import_bases():
        if is_ST2():
            import ViewInBrowserCommand
        else:
            ViewInBrowserCommand = __import__('View In Browser').ViewInBrowserCommand
        return ViewInBrowserCommand.ViewInBrowserCommand,

    def __new__(cls, view):
        patch_class(cls, 'View In Browser')
        return super(ElmViewInBrowserProxyCommand, cls).__new__(cls)

    def run(self, edit, path):
        self.path = path
        super(ElmViewInBrowserProxyCommand, self).run(edit)

    def normalizePath(self, fileToOpen): # override
        return super(ElmViewInBrowserProxyCommand, self).normalizePath(self.path)
