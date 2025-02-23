from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tools import log_check_call
from bootstrapvz.common.tools import rel_path
from . import locale
import logging
import os


class ValidateTrustedKeys(Task):
    description = 'Validate apt trusted keys'
    phase = phases.validation

    @classmethod
    def run(cls, info):
        from bootstrapvz.common.tools import log_call

        for i, rel_key_path in enumerate(info.manifest.packages.get('trusted-keys', {})):
            key_path = rel_path(info.manifest.path, rel_key_path)
            if not os.path.isfile(key_path):
                info.manifest.validation_error('File not found: {}'.format(key_path),
                                               ['packages', 'trusted-keys', i])

            from tempfile import mkdtemp
            from shutil import rmtree
            tempdir = mkdtemp()

            status, _, _ = log_call(
                ['gpg', '--quiet',
                 '--homedir', tempdir,
                 '--keyring', key_path,
                 '-k']
            )

            rmtree(tempdir)

            if status != 0:
                info.manifest.validation_error('Invalid GPG keyring: {}'.format(key_path),
                                               ['packages', 'trusted-keys', i])


class AddManifestSources(Task):
    description = 'Adding sources from the manifest'
    phase = phases.preparation

    @classmethod
    def run(cls, info):
        for name, lines in info.manifest.packages['sources'].items():
            for line in lines:
                info.source_lists.add(name, line)


class AddDefaultSources(Task):
    description = 'Adding default release sources'
    phase = phases.preparation
    predecessors = [AddManifestSources]

    @classmethod
    def run(cls, info):
        from bootstrapvz.common.releases import sid, wheezy, stretch, buster, bullseye, bookworm, trixie
        include_src = info.manifest.packages.get('include-source-type', False)
        components = ' '.join(info.manifest.packages.get('components', ['main']))
        info.source_lists.add('main', 'deb     {apt_mirror} {system.release} ' + components)
        if include_src:
            info.source_lists.add('main', 'deb-src {apt_mirror} {system.release} ' + components)
        if info.manifest.release != sid and info.manifest.release >= stretch:
            
            if info.manifest.release != sid and info.manifest.release >= bullseye:
                info.source_lists.add('main', 'deb     {apt_security} {system.release}-security ' + components)
                if include_src:
                    info.source_lists.add('main', 'deb-src {apt_security} {system.release}-security ' + components)
            else:
                info.source_lists.add('main', 'deb     {apt_security} {system.release}/updates ' + components)
                if include_src:
                    info.source_lists.add('main', 'deb-src {apt_security} {system.release}/updates ' + components)
            info.source_lists.add('main', 'deb     {apt_mirror} {system.release}-updates ' + components)
            if include_src:
                info.source_lists.add('main', 'deb-src {apt_mirror} {system.release}-updates ' + components)


class AddBackports(Task):
    description = 'Adding backports to the apt sources'
    phase = phases.preparation
    predecessors = [AddDefaultSources]

    @classmethod
    def run(cls, info):
        from bootstrapvz.common.releases import testing
        from bootstrapvz.common.releases import unstable
        if info.source_lists.target_exists('{system.release}-backports'):
            msg = ('{system.release}-backports target already exists').format(**info.manifest_vars)
            logging.getLogger(__name__).info(msg)
        elif info.manifest.release == testing:
            logging.getLogger(__name__).info('There are no backports for testing')
        elif info.manifest.release == unstable:
            logging.getLogger(__name__).info('There are no backports for sid/unstable')
        else:
            info.source_lists.add('backports', 'deb     {apt_mirror} {system.release}-backports main')
            info.source_lists.add('backports', 'deb-src {apt_mirror} {system.release}-backports main')


class AddManifestPreferences(Task):
    description = 'Adding preferences from the manifest'
    phase = phases.preparation

    @classmethod
    def run(cls, info):
        for name, preferences in info.manifest.packages['preferences'].items():
            info.preference_lists.add(name, preferences)


class InstallTrustedKeys(Task):
    description = 'Installing trusted keys'
    phase = phases.package_installation

    @classmethod
    def run(cls, info):
        from shutil import copy
        for rel_key_path in info.manifest.packages['trusted-keys']:
            key_path = rel_path(info.manifest.path, rel_key_path)
            key_name = os.path.basename(key_path)
            destination = os.path.join(info.root, 'etc/apt/trusted.gpg.d', key_name)
            copy(key_path, destination)
            os.chmod(destination, 0o644)


class WriteConfiguration(Task):
    decription = 'Write configuration to apt.conf.d from the manifest'
    phase = phases.package_installation

    @classmethod
    def run(cls, info):
        for name, val in info.manifest.packages.get('apt.conf.d', {}).items():
            if name == 'main':
                path = os.path.join(info.root, 'etc/apt/apt.conf')
            else:
                path = os.path.join(info.root, 'etc/apt/apt.conf.d', name)

            with open(path, 'w') as conf_file:
                conf_file.write(val + '\n')


class WriteSources(Task):
    description = 'Writing aptitude sources to disk'
    phase = phases.package_installation
    predecessors = [InstallTrustedKeys]

    @classmethod
    def run(cls, info):
        if not info.source_lists.target_exists(info.manifest.system['release']):
            log = logging.getLogger(__name__)
            log.warn('No default target has been specified in the sources list, '
                     'installing packages may fail')
        for name, sources in info.source_lists.sources.items():
            if name == 'main':
                list_path = os.path.join(info.root, 'etc/apt/sources.list')
            else:
                list_path = os.path.join(info.root, 'etc/apt/sources.list.d/', name + '.list')
            with open(list_path, 'w') as source_list:
                for source in sources:
                    source_list.write(str(source) + '\n')


class WritePreferences(Task):
    description = 'Writing aptitude preferences to disk'
    phase = phases.package_installation

    @classmethod
    def run(cls, info):
        for name, preferences in info.preference_lists.preferences.items():
            if name == 'main':
                list_path = os.path.join(info.root, 'etc/apt/preferences')
            else:
                list_path = os.path.join(info.root, 'etc/apt/preferences.d/', name)
            with open(list_path, 'w') as preference_list:
                for preference in preferences:
                    preference_list.write(str(preference) + '\n')


class DisableDaemonAutostart(Task):
    description = 'Disabling daemon autostart'
    phase = phases.package_installation

    @classmethod
    def run(cls, info):
        rc_policy_path = os.path.join(info.root, 'usr/sbin/policy-rc.d')
        with open(rc_policy_path, 'w') as rc_policy:
            rc_policy.write(('#!/bin/sh\n'
                             'exit 101'))
        os.chmod(rc_policy_path, 0o755)
        initictl_path = os.path.join(info.root, 'sbin/initctl')
        with open(initictl_path, 'w') as initctl:
            initctl.write(('#!/bin/sh\n'
                           'exit 0'))
        os.chmod(initictl_path, 0o755)


class AptUpdate(Task):
    description = 'Updating the package cache'
    phase = phases.package_installation
    predecessors = [locale.GenerateLocale, WriteConfiguration, WriteSources, WritePreferences]

    @classmethod
    def run(cls, info):
        log_check_call(['chroot', info.root,
                        'apt-get', 'update'])


class AptUpgrade(Task):
    description = 'Upgrading packages and fixing broken dependencies'
    phase = phases.package_installation
    predecessors = [AptUpdate, DisableDaemonAutostart]

    @classmethod
    def run(cls, info):
        from subprocess import CalledProcessError
        try:
            log_check_call(['chroot', info.root,
                            'apt-get', 'install',
                                       '--fix-broken',
                                       '--no-install-recommends',
                                       '--assume-yes'])
            log_check_call(['chroot', info.root,
                            'apt-get', 'upgrade',
                                       '--no-install-recommends',
                                       '--assume-yes'])
        except CalledProcessError as e:
            if e.returncode == 100:
                msg = ('apt exited with status code 100. '
                       'This can sometimes occur when package retrieval times out or a package extraction failed. '
                       'apt might succeed if you try bootstrapping again.')
                logging.getLogger(__name__).warn(msg)
            raise


class PurgeUnusedPackages(Task):
    description = 'Removing unused packages'
    phase = phases.system_cleaning

    @classmethod
    def run(cls, info):
        log_check_call(['chroot', info.root,
                        'apt-get', 'autoremove',
                                   '--purge',
                                   '--assume-yes'])


class AptClean(Task):
    description = 'Clearing the aptitude cache'
    phase = phases.system_cleaning

    @classmethod
    def run(cls, info):
        log_check_call(['chroot', info.root,
                        'apt-get', 'clean'])

        lists = os.path.join(info.root, 'var/lib/apt/lists')
        for list_file in [os.path.join(lists, f) for f in os.listdir(lists)]:
            if os.path.isfile(list_file):
                os.remove(list_file)


class EnableDaemonAutostart(Task):
    description = 'Re-enabling daemon autostart after installation'
    phase = phases.system_cleaning

    @classmethod
    def run(cls, info):
        os.remove(os.path.join(info.root, 'usr/sbin/policy-rc.d'))
        os.remove(os.path.join(info.root, 'sbin/initctl'))
