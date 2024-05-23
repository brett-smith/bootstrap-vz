from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import apt
from bootstrapvz.common.tasks import packages
from bootstrapvz.common.tools import log_check_call
import os


class InstallGoogleComputeEngineInitPackages(Task):
    description = 'Installing Google Compute Engine Init packages.'
    phase = phases.preparation
    successors = [packages.AddManifestPackages]

    @classmethod
    def run(cls, info):
        info.packages.add('google-guest-agent')

