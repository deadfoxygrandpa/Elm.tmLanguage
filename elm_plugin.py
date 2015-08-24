import sublime
import sublime_plugin
import os.path as fs

# MARK: compatibility

def is_ST2():
    return sublime.version().startswith('2')

def import_module(path):
    names = path.split('.')
    index = 1 if is_ST2() else 0
    base = __import__(names[index])
    for name in names[index + 1:]:
        base = getattr(base, name)
    return base

def retry_on_main_thread(callback, *args, **kwargs):
    try:
        # ST2: RuntimeError: Must call on main thread
        callback(*args, **kwargs)
    except RuntimeError:
        sublime.set_timeout(lambda: callback(*args, **kwargs), 0)

def show_quick_panel(window, items, on_select, selected_index=-1, on_highlight=None):
    kwargs = {} if is_ST2() else dict(selected_index=selected_index, on_highlight=on_highlight)
    retry_on_main_thread(window.show_quick_panel, items, on_select, **kwargs)

# MARK: Sublime

def fetch_json(url, callback=None, *args, **kwargs):
    from package_control.clients.json_api_client import JSONApiClient
    from package_control.http_cache import HttpCache
    from threading import Thread
    if callback:
        worker = lambda: callback(fetch_json(url), *args, **kwargs)
        Thread(target=worker).start()
    else:
        settings = dict(cache=HttpCache(604800))
        return JSONApiClient(settings).fetch_json(url, prefer_cached=True)

# MARK: logging

def get_string(key, *args):
    strings = sublime.load_settings('Elm User Strings.sublime-settings')
    return strings.get('logging.prefix') + strings.get(key).format(*args)

def log_string(key, *args):
    def on_retry():
        settings = sublime.load_settings('Elm Language Support.sublime-settings')
        if settings.get('debug'):
            print(get_string(key, *args))

    retry_on_main_thread(on_retry)

# MARK: beware thar be dragons below

# defer import as long as possible in case plugin not loaded
def replace_base_class(path):
    def splice_bases(old_base, *extra_bases):
        try:
            new_base = import_module(path)
        except ImportError:
            module_name = path[:path.index('.')]
            log_string('logging.missing_plugin', module_name)
            return None
        else:
            return (new_base,) + extra_bases

    def monkey_patch(target_cls):
        if not hasattr(target_cls, 'is_patched'):
            new_bases = splice_bases(target_cls.__bases__)
            target_cls.is_patched = bool(new_bases)
            if new_bases:
                target_cls.__bases__ = new_bases

    def decorator(target_cls):
        def __new__(cls, *args, **kwargs):
            monkey_patch(target_cls)
            super_ = super(target_cls, cls).__new__
            # TypeError: object() takes no parameters
            return super_(cls) if super_ is object.__new__ else super_(cls, *args, **kwargs)

        assert '__new__' not in target_cls.__dict__
        # ST2: TypeError: unbound method __new__()
        target_cls.__new__ = classmethod(__new__)
        return target_cls

    return decorator
