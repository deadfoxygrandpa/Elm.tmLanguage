import collections
import webbrowser

from datetime import datetime

try:     # ST3
    from .elm_plugin import *
except:  # ST2
    from elm_plugin import *

class ElmPackageOpenCommand(sublime_plugin.WindowCommand):
    Package = collections.namedtuple('Package', [
        'name',
        'description',
        'version',
        'repo_url',
        'open_url'])

    def run(self, json_url, repo_url, open_url, default_url, default_package, detail_format):
        def on_fetch(json):
            default_item = self.Package(
                name=default_package,
                description='',
                version=None,
                repo_url=None,
                open_url=default_url)
            decode_package = lambda json: self.decode_package(json, repo_url, open_url)
            self.packages = [default_item] + list(map(decode_package, json))
            self.show_packages(detail_format)

        fetch_json(json_url, on_fetch)

    def decode_package(self, json, repo_url, open_url):
        name = json['name']
        return self.Package(
            name=name,
            description=json['summary'],
            version=json['versions'][0],
            repo_url=repo_url.format(name=name),
            open_url=open_url.format(name=name))

    def show_packages(self, detail_format):
        format_entry = lambda package: [package.name, package.description]
        entries = list(map(format_entry, self.packages))
        on_highlight = lambda index: self.on_highlight(index, detail_format)
        show_quick_panel(self.window, entries, self.on_select, on_highlight=on_highlight)

    def on_select(self, index):
        if index != -1:
            package = self.packages[index]
            webbrowser.open_new_tab(package.open_url)

    def on_highlight(self, index, detail_format):
        def on_fetch(json):
            if index == self.highlighted_index:
                forks = json['forks_count']
                stars = json['stargazers_count']
                watchers = json['subscribers_count']
                sublime.status_message(detail_format.format(
                    name=package.name,
                    version=package.version,
                    date=datetime.strptime(json['pushed_at'], "%Y-%m-%dT%H:%M:%SZ"),
                    rating=((forks + 1) * (stars + 1) * (watchers + 1)) ** (1.0 / 3)))

        self.highlighted_index = index
        package = self.packages[index]
        if package.repo_url:
            fetch_json(package.repo_url, on_fetch)
