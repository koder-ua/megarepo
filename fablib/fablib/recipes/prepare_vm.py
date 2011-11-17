def prepare_vm():
    replace_in_file("/etc/default/grub",
            'GRUB_TIMEOUT=\d+$',
            'GRUB_TIMEOUT=0',
            use_sudo=True)

    replace_in_file("/etc/default/grub",
            '#?GRUB_HIDDEN_TIMEOUT=\d+$',
            'GRUB_HIDDEN_TIMEOUT=0',
            use_sudo=True)

    replace_in_file("/etc/default/grub",
            '#?GRUB_HIDDEN_TIMEOUT_QUIET=.*$',
            'GRUB_HIDDEN_TIMEOUT_QUIET=true',
            use_sudo=True)

    sudo('update-grub')
    