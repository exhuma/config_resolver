import fabric.api as fab


@fab.task
def autotest():
    '''
    Set up automatic test runner with pytest and inotify.
    '''
    with fab.quiet():
        result = fab.local('which inotifywait > /dev/null')
        if result.failed:
            print("inotifywait not available")
            return

    with fab.shell_env(PYTHONWARNINGS=''), fab.settings(warn_only=True):
        print("Waiting for changes...")
        while True:
            fab.local(
                'inotifywait '
                '--exclude "\\.*\\.sw[px]" '
                '-r '
                '-e close_write,moved_to,create '
                'config_resolver tests')
            fab.local('pipenv run pytest tests')
