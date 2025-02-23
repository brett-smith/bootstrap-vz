import os.path

from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import kernel


class InstallDHCPCD(Task):
    description = 'Replacing isc-dhcp with dhcpcd'
    phase = phases.preparation

    @classmethod
    def run(cls, info):
        # isc-dhcp-client before jessie doesn't work properly with ec2
        info.packages.add('dhcpcd')
        info.exclude_packages.add('isc-dhcp-client')
        info.exclude_packages.add('isc-dhcp-common')


class EnableDHCPCDDNS(Task):
    description = 'Configuring the DHCP client to set the nameservers'
    phase = phases.system_modification

    @classmethod
    def run(cls, info):
        from bootstrapvz.common.tools import sed_i
        dhcpcd = os.path.join(info.root, 'etc/default/dhcpcd')
        sed_i(dhcpcd, '^#*SET_DNS=.*', 'SET_DNS=\'yes\'')


class AddBuildEssentialPackage(Task):
    description = 'Adding build-essential package'
    phase = phases.preparation

    @classmethod
    def run(cls, info):
        info.packages.add('build-essential')


class InstallNetworkingUDevHotplugAndDHCPSubinterface(Task):
    description = 'Setting up udev and DHCPD rules for EC2 networking'
    phase = phases.system_modification

    @classmethod
    def run(cls, info):
        from . import assets
        script_src = os.path.join(assets, 'ec2')
        script_dst = os.path.join(info.root, 'etc')

        import stat
        rwxr_xr_x = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                     stat.S_IRGRP                | stat.S_IXGRP |
                     stat.S_IROTH                | stat.S_IXOTH)

        from shutil import copy
        copy(os.path.join(script_src, '53-ec2-network-interfaces.rules'),
             os.path.join(script_dst, 'udev/rules.d/53-ec2-network-interfaces.rules'))
        os.chmod(os.path.join(script_dst, 'udev/rules.d/53-ec2-network-interfaces.rules'), rwxr_xr_x)

        os.mkdir(os.path.join(script_dst, 'sysconfig'), 0o755)
        os.mkdir(os.path.join(script_dst, 'sysconfig/network-scripts'), 0o755)
        copy(os.path.join(script_src, 'ec2net.hotplug'),
             os.path.join(script_dst, 'sysconfig/network-scripts/ec2net.hotplug'))
        os.chmod(os.path.join(script_dst, 'sysconfig/network-scripts/ec2net.hotplug'), rwxr_xr_x)

        copy(os.path.join(script_src, 'ec2net-functions'),
             os.path.join(script_dst, 'sysconfig/network-scripts/ec2net-functions'))
        os.chmod(os.path.join(script_dst, 'sysconfig/network-scripts/ec2net-functions'), rwxr_xr_x)

        copy(os.path.join(script_src, 'ec2dhcp.sh'),
             os.path.join(script_dst, 'dhcp/dhclient-exit-hooks.d/ec2dhcp.sh'))
        os.chmod(os.path.join(script_dst, 'dhcp/dhclient-exit-hooks.d/ec2dhcp.sh'), rwxr_xr_x)

        with open(os.path.join(script_dst, 'network/interfaces'), "a") as interfaces:
            interfaces.write("iface eth1 inet dhcp\n")
            interfaces.write("iface eth2 inet dhcp\n")
            interfaces.write("iface eth3 inet dhcp\n")
            interfaces.write("iface eth4 inet dhcp\n")
            interfaces.write("iface eth5 inet dhcp\n")
            interfaces.write("iface eth6 inet dhcp\n")
            interfaces.write("iface eth7 inet dhcp\n")


class InstallEnhancedNetworking(Task):
    description = 'Installing enhanced networking kernel driver using DKMS'
    phase = phases.system_modification
    successors = [kernel.UpdateInitramfs]

    @classmethod
    def run(cls, info):
        from bootstrapvz.common.releases import stretch, buster, bullseye, bookworm, trixie
        if info.manifest.release >= bookworm:
            version = '4.18.9'
            drivers_url = 'https://downloads.sourceforge.net/project/e1000/ixgbevf%20stable/4.18.9/ixgbevf-4.18.9.tar.gz'
        elif info.manifest.release >= bullseye:
            version = '4.18.9'
            drivers_url = 'https://downloads.sourceforge.net/project/e1000/ixgbevf%20stable/4.18.9/ixgbevf-4.18.9.tar.gz'
        elif info.manifest.release >= buster:
            version = '4.16.5'
            drivers_url = 'https://master.dl.sourceforge.net/project/e1000/ixgbevf%20stable/4.16.5/ixgbevf-4.16.5.tar.gz'
        elif info.manifest.release >= stretch:
            version = '4.3.4'
            drivers_url = 'https://master.dl.sourceforge.net/project/e1000/ixgbevf%20stable/4.3.4/ixgbevf-4.3.4.tar.gz'
        else:
            version = '3.2.2'
            drivers_url = 'https://master.dl.sourceforge.net/project/e1000/ixgbevf%20stable/3.2.2/ixgbevf-3.2.2.tar.gz'
        archive = os.path.join(info.root, 'tmp', 'ixgbevf-%s.tar.gz' % (version))
        module_path = os.path.join(info.root, 'usr', 'src', 'ixgbevf-%s' % (version))

        import urllib.request, urllib.parse, urllib.error
        urllib.request.urlretrieve(drivers_url, archive)

        from bootstrapvz.common.tools import log_check_call
        log_check_call(['tar', '--ungzip',
                               '--extract',
                               '--file', archive,
                               '--directory', os.path.join(info.root, 'usr',
                                                           'src')])

        with open(os.path.join(module_path, 'dkms.conf'), 'w') as dkms_conf:
            dkms_conf.write("""PACKAGE_NAME="ixgbevf"
PACKAGE_VERSION="%s"
CLEAN="cd src/; sed -i '1s/^/EXTRA_CFLAGS := -fno-pie/' Makefile && make clean"
MAKE="cd src/; make BUILD_KERNEL=${kernelver}"
BUILT_MODULE_LOCATION[0]="src/"
BUILT_MODULE_NAME[0]="ixgbevf"
DEST_MODULE_LOCATION[0]="/updates"
DEST_MODULE_NAME[0]="ixgbevf"
AUTOINSTALL="yes"
""" % (version))

        for task in ['add', 'build', 'install']:
            # Invoke DKMS task using specified kernel module (-m) and version (-v)
            log_check_call(['chroot', info.root,
                            'dkms', task, '-m', 'ixgbevf', '-v', version, '-k',
                            info.kernel_version])


class InstallENANetworking(Task):
    description = 'Installing ENA networking kernel driver using DKMS'
    phase = phases.system_modification
    successors = [kernel.UpdateInitramfs]

    @classmethod
    def run(cls, info):
        version = info.manifest.provider.get('amzn-driver-version', 'master')

        if version != 'master':
            version = 'ena_linux_' + version

        drivers_url = 'https://codeload.github.com/amzn/amzn-drivers/tar.gz/' + version
        module_path = os.path.join(info.root, 'usr', 'src',
                                   'amzn-drivers-%s' % (version))
        archive = os.path.join(info.root, 'tmp', 'amzn-drivers-%s.tar.gz' % (version))

        import urllib.request, urllib.parse, urllib.error
        urllib.request.urlretrieve(drivers_url, archive)

        from bootstrapvz.common.tools import log_check_call
        log_check_call(['tar', '--ungzip',
                               '--extract',
                               '--file', archive,
                               '--directory', os.path.join(info.root, 'usr',
                                                           'src')])

        with open(os.path.join(module_path, 'dkms.conf'), 'w') as dkms_conf:
            dkms_conf.write("""PACKAGE_NAME="ena"
PACKAGE_VERSION="%s"
CLEAN="make -C kernel/linux/ena clean"
MAKE="make -C kernel/linux/ena/ BUILD_KERNEL=${kernelver}"
BUILT_MODULE_NAME[0]="ena"
BUILT_MODULE_LOCATION="kernel/linux/ena"
DEST_MODULE_LOCATION[0]="/updates"
DEST_MODULE_NAME[0]="ena"
AUTOINSTALL="yes"
""" % (version))

        for task in ['add', 'build', 'install']:
            # Invoke DKMS task using specified kernel module (-m) and version (-v)
            log_check_call(['chroot', info.root,
                            'dkms', task, '-m', 'amzn-drivers', '-v', version,
                            '-k', info.kernel_version])
