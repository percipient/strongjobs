from os import path
from subprocess import PIPE, Popen


class GitRepo(object):
    class RunError(RuntimeError):
        pass

    def __init__(self, root_path, repo_path):
        self.path = repo_path
        self.directory = path.join(root_path, self.path)

        # Clone the repo if it isn't there.
        if not path.exists(self.directory):
            proc = Popen(['git', 'clone', 'ssh://git@github.com/' + self.path, self.directory], stdout=PIPE, stderr=PIPE)
            proc.wait()
            if proc.returncode is not 0:
                raise GitRepo.RunError(proc.stderr.read())

    def run(self, *args):
        args = ('git', '--git-dir=' + path.join(self.directory, '.git'), '--work-tree=' + self.directory) + args
        proc = Popen(args, cwd=self.directory, stdout=PIPE, stderr=PIPE)
        proc.wait()
        if proc.returncode is not 0:
            raise GitRepo.RunError(proc.stderr.read())

        return proc.stdout.read()

    def update(self):
        self.run('reset', '--hard')
        self.run('checkout', 'master')
        self.run('pull')

        # Clean-up upstream branches.
        self.run('remote', 'prune', 'origin')

        # Delete all local branches (to get a pristine state).
        branches = self.run('branch')
        branches = [branch[2:] for branch in branches.split('\n') if branch and branch[2:] != 'master']
        if branches:
            self.run('branch', '-D', *branches)
