import sublime
import os.path as fs

if int(sublime.version()) < 3000:
    from elm_project import ElmProject
    from ViewInBrowserCommand import ViewInBrowserCommand
else:
    from .elm_project import ElmProject
    ViewInBrowserCommand = __import__('View In Browser').ViewInBrowserCommand.ViewInBrowserCommand

class ElmOpenInBrowserCommand(ViewInBrowserCommand):

    def run(self, edit):
        super(ElmOpenInBrowserCommand, self).run(edit)

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def normalizePath(self, fileToOpen): # ViewInBrowserCommand
        norm_path = fs.join(self.project.working_dir, fs.expanduser(self.project.html_path))
        return super(ElmOpenInBrowserCommand, self).normalizePath(fs.abspath(norm_path))
