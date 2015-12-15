import webbrowser

try:     # ST3
    import urllib.parse as urlparse
    import urllib.request as urllib

    from .elm_plugin import *
    from .elm_project import ElmProject
except:  # ST2
    import urlparse
    import urllib

    from elm_plugin import *
    from elm_project import ElmProject

class ElmOpenInBrowserCommand(sublime_plugin.TextCommand):

    def is_enabled(self):
        self.project = ElmProject(self.view.file_name())
        return self.project.exists

    def run(self, edit):
        norm_path = fs.join(self.project.working_dir, fs.expanduser(self.project.html_path))
        file_path = fs.abspath(norm_path)
        if fs.isfile(file_path):
            # http://stackoverflow.com/questions/11687478/convert-a-filename-to-a-file-url#comment32679033_14298190
            file_url = urlparse.urljoin('file:', urllib.pathname2url(file_path))
            # inspired by https://github.com/noahcoad/open-url
            webbrowser.open_new_tab(file_url)
        else:
            sublime.status_message(get_string('open_in_browser.not_found', html_path))
