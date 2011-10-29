import os.path

from fabric.api import prefix, run, sudo

from fablib.core import install, PackageManager

class PIPInstaller(PackageManager):
    
    @classmethod
    def do_install_package(cls, requirement):
        sudo('pip install {}'.format(requirement))
    
    @classmethod
    def get_all_installed(cls):
        res = {}
        for line in run('pip freeze').split('\n'):
            package, ver = line.split('==')
            res[package] = ver
        return res

def py_install(module, ver = None):
    if ver is None:
        PIPInstaller.install_package(module)
    else:
        PIPInstaller.install_package("{}=={}".format(module, ver))

pip = py_install

def python_venv_init(py_ver, path):
    install("python=={}".format(py_ver))
    install("python-pip")
    pip('virtualenv')
    run('virtualenv --no-site-packages {}'.format(path))

def v_env(path):
    return prefix("source {}".format(os.path.join(path,'bin/activate')))


