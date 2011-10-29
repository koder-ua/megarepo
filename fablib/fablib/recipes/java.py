import os

from fabric.api import *
from fabric.context_managers import *
from fabric.contrib.files import exists

from fablib.core import provides, provides_pkg, ensure, install, check_cmd,\
                        put_rf, get_rf

from fablib.fab_os import add_apt_sources
from fablib.wget import wget

def install_deb_java():
    install_deb_java_jdk()
    install_deb_java_jre()

@provides('javac')
@provides_pkg('sun-java6-jdk')
def install_deb_java_jdk():
    add_apt_sources(True,
                    'deb http://archive.canonical.com/ lucid partner')
    sudo("sh -c 'echo sun-java6-jdk shared/accepted-sun-dlj-v1-1 select" + \
                     " true " + \
                     "| /usr/bin/debconf-set-selections';")
    install('sun-java6-jdk')   
    
@provides('java')
@provides_pkg('sun-java6-jre')
def install_deb_java_jre():
    add_apt_sources(True,
                    'deb http://archive.canonical.com/ lucid partner')
    sudo("sh -c 'echo sun-java6-jre shared/accepted-sun-dlj-v1-1 select " + \
                       "true | /usr/bin/debconf-set-selections';")
    install('sun-java6-jre')   

@ensure('expect')
def install_oracle_java(ver='1.6.0_27'):
    
    if ver != '1.6.0_27':
        raise RuntimeError("Only '1.6.0_27' version of java support by now")
    
    JAVAC = check_cmd('javac')
    JAVA_RT = check_cmd('java')
    
    if JAVAC and JAVA_RT:
        return
    
    JAVAH = '/usr/local/java'
    
    JDK_DIR = os.path.join(JAVAH, 'jdk1.6.0_27')
    JRE_DIR = os.path.join(JAVAH, 'jre1.6.0_27')
    
    JDK_URL = 'http://download.oracle.com/otn-pub/java/jdk/6u27-b07/jdk-6u27-linux-x64.bin'
    JRE_URL = 'http://download.oracle.com/otn-pub/java/jdk/6u27-b07/jre-6u27-linux-x64.bin'
    
    if not exists(JAVAH):
        sudo('mkdir ' + JAVAH)

    with cd(JAVAH):
        expect_cmd = 'spawn sh {0};' + \
                     ' expect "Press Enter to continue.....\\n"; send "\\n"'
        
        if not exists(os.path.join(JDK_DIR,'bin/javac')):
            
            if exists(JDK_DIR):
                sudo('rm -rf {0}/*'.format(JDK_DIR))
                
            wget(JDK_URL, use_sudo=True)    
            sudo("expect -c '{0}'".format(
                expect_cmd.format('jdk-6u27-linux-x64.bin')))
            sudo('rm ' + 'jdk-6u27-linux-x64.bin')
            
        if not exists(os.path.join(JRE_DIR,'bin/java')):
            
            if exists(JRE_DIR):
                sudo('rm -rf {0}/*'.format(JRE_DIR))
            
            wget(JRE_URL, use_sudo=True)    
            sudo("expect -c '{0}'".format(
                expect_cmd.format('jre-6u27-linux-x64.bin')))
            sudo('rm ' + 'jre-6u27-linux-x64.bin')
    ln1 = 'export JAVA_HOME=' + JRE_DIR
    ln2 = 'export PATH="$PATH:{0}/bin:{1}/bin"'.format(JRE_DIR, JDK_DIR)
    
    profile = get_rf('/etc/profile')
    put_rf('/etc/profile',
           "\n".join((profile, ln1, ln2, '')),
           use_sudo=True)
