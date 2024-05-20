from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import apt
from bootstrapvz.common.tasks import packages
from bootstrapvz.common.tools import log_check_call
import os

class AddGPG(Task):
    description = 'Add packages for google bootstrap setup'
    phase = phases.preparation

    @classmethod
    def run(cls, info):
        info.include_packages.add('gpg')
        info.include_packages.add('gpg-agent')

class AddGoogleCloudRepoKey(Task):
    description = 'Adding Google Cloud Repo key.'
    phase = phases.package_installation
    predecessors = [apt.InstallTrustedKeys]
    successors = [apt.WriteSources]

    @classmethod
    def run(cls, info):
        key_file = os.path.join(info.root, 'google.gpg.key')
        log_check_call(['wget', 'https://packages.cloud.google.com/apt/doc/apt-key.gpg', '-O', key_file])
        log_check_call(['chroot', info.root, 'apt-key', 'add', 'google.gpg.key'])
        os.remove(key_file)

class AddGoogleCloudRepo(Task):
    description = 'Adding Google Cloud Repo.'
    phase = phases.preparation
    predecessors = [apt.AddManifestSources]

    @classmethod
    def run(cls, info):
        info.source_lists.add('google-cloud-sdk', 'deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main')

class CleanupBootstrapRepoKey(Task):
    description = 'Cleaning up bootstrap repo key.'
    phase = phases.system_cleaning

    @classmethod
    def run(cls, info):
        os.remove(os.path.join(info.root, 'etc', 'apt', 'trusted.gpg'))
