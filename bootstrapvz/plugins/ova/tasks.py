from bootstrapvz.base import Task
from bootstrapvz.common import phases
from bootstrapvz.common.tasks import workspace
import os
import shutil

assets = os.path.normpath(os.path.join(os.path.dirname(__file__), 'assets'))


class CheckOVAPath(Task):
	description = 'Checking if the OVA file already exists'
	phase = phases.preparation

	@classmethod
	def run(cls, info):
		ova_basename = info.manifest.name.format(**info.manifest_vars)
		ova_name = ova_basename + '.ova'
		ova_path = os.path.join(info.manifest.bootstrapper['workspace'], ova_name)
		if os.path.exists(ova_path):
			from bootstrapvz.common.exceptions import TaskError
			msg = 'The OVA `{name}\' already exists at `{path}\''.format(name=ova_name, path=ova_path)
			raise TaskError(msg)
		info._ova['ova_basename'] = ova_basename
		info._ova['ova_name'] = ova_name
		info._ova['ova_path'] = ova_path


class CreateOVADir(Task):
	description = 'Creating directory for the OVA'
	phase = phases.preparation
	predecessors = [workspace.CreateWorkspace, CheckOVAPath]

	@classmethod
	def run(cls, info):
		info._ova['folder'] = os.path.join(info.workspace, 'ova')
		os.mkdir(info._ova['folder'])


class PackageOVA(Task):
	description = 'Packaging the volume as an OVA'
	phase = phases.image_registration

	@classmethod
	def run(cls, info):
		import random
		mac_address = '080027{mac:06X}'.format(mac=random.randrange(16 ** 6))
		
		from bootstrapvz.common.tools import log_check_call
		disk_name = info._ova['ova_basename'] + '.' + info.volume.extension
		disk_link = os.path.join(info._ova['folder'], disk_name)
		log_check_call(['ln', '-s', info.volume.image_path, disk_link])

		ovf_path = os.path.join(info._ova['folder'], info._ova['ova_basename'] + '.ovf')
		cls.write_ovf(info, ovf_path, mac_address, disk_name)

		ova_files = os.listdir(info._ova['folder'])
		log_check_call(['ovftool', '--shaAlgorithm=SHA1', ovf_path, info._ova['ova_path']]
		               )
		import logging
		logging.getLogger(__name__).info('The OVA has been placed at ' + info._ova['ova_path'])

	@classmethod
	def write_ovf(cls, info, destination, mac_address, disk_name):
		namespaces = {'ovf':     'http://schemas.dmtf.org/ovf/envelope/1',
		              'rasd':    'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData',
		              'vssd':    'http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData',
		              'xsi':     'http://www.w3.org/2001/XMLSchema-instance',
		              'vbox':    'http://www.virtualbox.org/ovf/machine',
		              }

		def attr(element, name, value=None):
			for prefix, ns in namespaces.iteritems():
				name = name.replace(prefix + ':', '{' + ns + '}')
			if value is None:
				return element.attrib[name]
			else:
				element.attrib[name] = str(value)

		template_path = os.path.join(assets, 'default.ovf')
		if 'ovf' in info.manifest.plugins['ova']:
			template_path = info.manifest.plugins['ova']['ovf']
		
		import xml.etree.ElementTree as ET
		template = ET.parse(template_path)
		root = template.getroot()

		[disk_ref] = root.findall('./ovf:References/ovf:File', namespaces)
		attr(disk_ref, 'ovf:href', disk_name)

		# List of OVF disk format URIs
		# Snatched from VBox source (src/VBox/Main/src-server/ApplianceImpl.cpp:47)
		# ISOURI = "http://www.ecma-international.org/publications/standards/Ecma-119.htm"
		# VMDKStreamURI = "http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"
		# VMDKSparseURI = "http://www.vmware.com/specifications/vmdk.html#sparse"
		# VMDKCompressedURI = "http://www.vmware.com/specifications/vmdk.html#compressed"
		# VMDKCompressedURI2 = "http://www.vmware.com/interfaces/specifications/vmdk.html#compressed"
		# VHDURI = "http://go.microsoft.com/fwlink/?LinkId=137171"
		volume_uuid = info.volume.get_uuid()
		[disk] = root.findall('./ovf:DiskSection/ovf:Disk', namespaces)
		attr(disk, 'ovf:capacity', info.volume.size.bytes.get_qty_in('B'))
		attr(disk, 'ovf:format', info.volume.ovf_uri)
		attr(disk, 'vbox:uuid', volume_uuid)

		[system] = root.findall('./ovf:VirtualSystem', namespaces)
		attr(system, 'ovf:id', info._ova['ova_basename'])

		# Set the operating system
		[os_section] = system.findall('./ovf:OperatingSystemSection', namespaces)
		os_info = {'i386': {'id': 96, 'name': 'Debian'},
		           'amd64': {'id': 96, 'name': 'debian6_64Guest'}
		           }.get(info.manifest.system['architecture'])
		attr(os_section, 'ovf:id', os_info['id'])
		[os_desc] = os_section.findall('./ovf:Description', namespaces)
		os_desc.text = os_info['name']
		[os_type] = os_section.findall('./vbox:OSType', namespaces)
		os_type.text = os_info['name']

		[sysid] = system.findall('./ovf:VirtualHardwareSection/ovf:System/'
		                         'vssd:VirtualSystemIdentifier', namespaces)
		sysid.text = info._ova['ova_basename']

		[machine] = system.findall('./vbox:Machine', namespaces)
		import uuid
		del machine.attrib['uuid']
		attr(machine, 'uuid', uuid.uuid4())
		del machine.attrib['name']
		attr(machine, 'name', info._ova['ova_basename'])
		from datetime import datetime
		del machine.attrib['lastStateChange']
		attr(machine, 'lastStateChange', datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))
		[nic] = machine.findall('./ovf:Hardware/ovf:Network/ovf:Adapter', namespaces)
		attr(machine, 'MACAddress', mac_address)

		[device_img] = machine.findall('./ovf:StorageControllers'
		                               '/ovf:StorageController[1]'
		                               '/ovf:AttachedDevice/ovf:Image', namespaces)
		attr(device_img, 'uuid', '{' + str(volume_uuid) + '}')

		template.write(destination, xml_declaration=True)  # , default_namespace=namespaces['ovf']


class RemoveOVADir(Task):
	description = 'Removing the OVA directory'
	phase = phases.cleaning
	successors = [workspace.DeleteWorkspace]

	@classmethod
	def run(cls, info):
		shutil.rmtree(info._ova['folder'])
		del info._ova['folder']
