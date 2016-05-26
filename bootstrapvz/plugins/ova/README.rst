OVA
---

Open Virtualization Format (OVF) is an open standard for packaging and distributing
virtual appliances or, more generally, software to be run in virtual machines. 
<http://en.wikipedia.org/wiki/Open_Virtualization_Format>`__

This plugin creates am OVA that is ready to be shared or
deployed. Currently this requires that VMWare's ovftool is installed. 
<https://my.vmware.com/group/vmware/details?productId=491&downloadGroup=OVFTOOL410>

Settings
~~~~~~~~

-  ``ovf``: An optional path to an OVF template to use in place of the
	default, allowing customisation of memory, network, storage and more.
   Default: ``<default.ovf>``.
   ``optional``
