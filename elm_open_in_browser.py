try:     # ST3
    from .elm_plugin import *
    from .elm_project import ElmProject
except:  # ST2
    from elm_plugin import *
    from elm_project import ElmProject

class ElmOpenInBrowserCommand(sublime_plugin.TextCommand):

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def run(self, edit):
        norm_path = fs.join(self.project.working_dir, fs.expanduser(self.project.html_path))
        html_path = fs.abspath(norm_path)
        if not fs.isfile(html_path):
            sublime.status_message(get_string('open_in_browser.not_found', html_path))
        elif ElmOpenInBrowserWithSbeCommand.is_patched:
            self.view.window().run_command('elm_open_in_browser_with_sbe', dict(paths=[html_path]))
        elif ElmOpenInBrowserWithVibCommand.is_patched:
            self.view.run_command('elm_open_in_browser_with_vib', dict(path=html_path))
        else:
            sublime.status_message(get_string('open_in_browser.missing_plugin'))

@replace_base_class('SideBarEnhancements.SideBar.SideBarOpenInBrowserCommand')
class ElmOpenInBrowserWithSbeCommand(sublime_plugin.WindowCommand):
    pass

@replace_base_class('View In Browser.ViewInBrowserCommand.ViewInBrowserCommand')
class ElmOpenInBrowserWithVibCommand(sublime_plugin.TextCommand):

    def run(self, edit, path):
        self.path = path
        super(ElmOpenInBrowserWithVibCommand, self).run(edit)

    def normalizePath(self, fileToOpen): # override
        return super(ElmOpenInBrowserWithVibCommand, self).normalizePath(self.path)
