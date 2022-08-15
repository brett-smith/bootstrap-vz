from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks.packages import InstallPackages


class DefaultPackages(Task):
    description = 'Adding image packages required for Azure'
    phase = phases.preparation

    @classmethod
    def run(cls, info):
        info.packages.add('openssl')
        info.packages.add('python-openssl')
        #info.packages.add('python-pyasn1')
        info.packages.add('python-setuptools')
        info.packages.add('sudo')
        info.packages.add('parted')
        info.packages.add('waagent')
        

        from bootstrapvz.common.tools import config_get, rel_path
        kernel_packages_path = rel_path(__file__, 'packages-kernels.yml')
        kernel_package = config_get(kernel_packages_path, [info.manifest.release.codename,
                                                           info.manifest.system['architecture']])
        info.packages.add(kernel_package)

