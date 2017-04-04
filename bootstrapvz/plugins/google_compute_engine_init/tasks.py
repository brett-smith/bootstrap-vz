from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import apt
from bootstrapvz.common.tasks import packages
from bootstrapvz.common.tools import log_check_call
import os


class AddGoogleComputeEngineInitRepos(Task):
    description = 'Adding Google Compute Engine Init repositories.'
    phase = phases.preparation
    predecessors = [apt.AddManifestSources]

    @classmethod
    def run(cls, info):
        info.source_lists.add('google-cloud-compute', 'deb http://packages.cloud.google.com/apt google-cloud-compute-{system.release} main')


class InstallGoogleComputeEngineInitPackages(Task):
    description = 'Installing Google Compute Engine Init packages.'
    phase = phases.preparation
    successors = [packages.AddManifestPackages]

    @classmethod
    def run(cls, info):
        info.packages.add('google-compute-engine-{system.release}')
        info.packages.add('google-compute-engine-init-{system.release}')
        info.packages.add('google-config-{system.release}')

