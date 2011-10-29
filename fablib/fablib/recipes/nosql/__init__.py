def remove_from_autoruns(cassandra=True,
                         mongodb=True):
    if cassandra:
        with settings(hide('warnings', 'stderr'), warn_only=True):
            sudo("rm /etc/rc0.d/*cassandra " + \
                 "/etc/rc1.d/*cassandra " +
                 "/etc/rc2.d/*cassandra " + \
                 "/etc/rc3.d/*cassandra " + \
                 "/etc/rc4.d/*cassandra " + \
                 "/etc/rc5.d/*cassandra /etc/rc6.d/*cassandra")

    if mongo:
        fl = get_rf('/etc/init/mongodb.conf')
        nfl = []
        for i in fl.split('\n'):
            if i.startswith('start on runlevel'):
                nfl.append('start on runlevel []')
            elif i.startswith('stop on runlevel'):
                nfl.append('stop on runlevel []')
            else:
                nfl.append(i)
        put_rf('/etc/init/mongodb.conf', "\n".join(nfl), use_sudo=True)
