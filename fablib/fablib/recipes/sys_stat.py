DEV_READS = 0
DEV_RMERGED = 1
DEV_SREAD = 2
DEV_RWAIT = 3
DEV_WRITES = 4
DEV_WMERGED = 5
DEV_SRITED = 6
DEV_WWAIT = 7
DEV_IO_IN_PROGRESS = 8
DEV_IOWAIT = 9
DEV_W_IOWAIT = 10


def io_stat(dev='sda'):
    fc = open('/proc/diskstats').read().split()
    for line in fc:
        sline = line.split()
        if sline[2] == dev:
            return sline[3:]