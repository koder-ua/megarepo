from fabric.context_managers import settings, hide
from fabric.api import sudo, run

class CMDExecutor(object):
    """Base implementation for local and SSH command executions"""
    def __init__(self):
        """Preconfigure class"""
        self.last_result = None
        self.last_stdout = None
        self.stdin = None
        self.deferred = []

    def getLastResult(self):
        """get last results"""
        if self.last_result is None:
            raise RuntimeError("no last result available")
        return self.last_result

    def execute(self,*cmd):
        """Execute command pure virtual func"""
        raise RuntimeError("Pure virtual fucntion call")

    def exec_simple_check(self,*cmd):
        """Execute command and check ret code"""
        res = self.exec_simple(*cmd)

        assert 0 == res, "Cmd %r exited with code %s. Output: %r" \
                        % (cmd, self.last_result, self.last_stdout)

    def exec_simple(self,*cmd):
        """execute command without checking return code"""
        stdout = []

        for i in self.execute(*cmd):
            stdout.append(i)

        self.last_stdout = "".join(stdout)

        return self.last_result


class FabCmdExecutor(CMDExecutor):
    def execute(self, *cmd):
        self.last_result = None
        
        with settings(hide('warnings'), warn_only=True):
            result = sudo(" ".join(cmd))
            
        self.last_stdout = str(result)
        self.last_result = result.return_code
        
        yield self.last_stdout
