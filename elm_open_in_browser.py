import sublime
import os.path as fs

if int(sublime.version()) < 3000:
    from elm_project import ElmProject
    from ViewInBrowserCommand import ViewInBrowserCommand as OpenInBrowserCommand
else:
    from .elm_project import ElmProject
    try:
        from SideBarEnhancements.SideBar import SideBarOpenInBrowserCommand as OpenInBrowserCommand
    except:
        OpenInBrowserCommand = __import__('View In Browser').ViewInBrowserCommand.ViewInBrowserCommand

class ElmOpenInBrowserCommand(OpenInBrowserCommand):

    def run(self, edit=None):
        if edit: # ViewInBrowserCommand
            super(ElmOpenInBrowserCommand, self).run(edit)
        else: # SideBarOpenInBrowserCommand
            super(ElmOpenInBrowserCommand, self).run([self.html_path()])

    def is_enabled(self):
        try: # ViewInBrowserCommand
            self.project = ElmProject(self.view.file_name())
        except: # SideBarOpenInBrowserCommand
            self.project = ElmProject(self.window.active_view().file_name())
        return self.project.exists

    def normalizePath(self, fileToOpen): # ViewInBrowserCommand
        return super(ElmOpenInBrowserCommand, self).normalizePath(self.html_path())

    def html_path(self):
        norm_path = fs.join(self.project.working_dir, fs.expanduser(self.project.html_path))
        return fs.abspath(norm_path)
