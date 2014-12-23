import os
import subprocess
import json
import threading
import Queue
import time
from collections import defaultdict

import sublime, sublime_plugin

class ElmLanguageSupportAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        return [('HELLO\tWHAT', 'this is weird')]
