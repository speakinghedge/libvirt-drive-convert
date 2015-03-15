''' Convert the format of disk images used by libvirt domains
    and adapt the domain configuration.

    Currently only support for qemu is implemented.
'''
import sys, os.path, subprocess
import libvirt
import argparse
from lxml import etree

class LibVirtDriveConvert:
    ''' libvirt disk image converter class '''

    DRIVER_TYPES = {
        'qemu' : {
            'formats' : {
                'raw'   : 'raw',
                'qcow2' : 'qcow2',
                'qcow'  : 'qcow',
                'cow'   : 'cow',
                'qed'   : 'qed',
                'vdi'   : 'vdi',
                'vmdk'  : 'vmdk'
            }
        }
    }

    def _get_info_from_dom_disk_nodes(self, dom_disk_nodes, dom_name):
        ''' Extract disk information from XML node definition.

        :param dom_disk_nodes: array of XML disk-elements
        :param dom_name: domain the entries belong to
        :returns: [{'xml_node': <object>, 'driver_name': <string>, \
                    'driver_type': <string>, 'source_file': <string>}]
        '''

        dom_disk_infos = []
        for dom_disk_node in dom_disk_nodes:

            # print etree.tostring(dom_disk_node)

            driver_name = None
            driver_type = None
            source_file = None
            try:
                driver_name = dom_disk_node.find('driver').get('name')
                if driver_name is None:
                    raise
                if driver_name not in self.DRIVER_TYPES:
                    sys.stderr.write('\ndomain \'%s\' is using a unknown \
                                      disk driver name \'%s\'. abort.\n\n' \
                                      % (args.dom_name, driver_name))
                    sys.exit(1)
            except all:
                sys.stderr.write('\nfailed to get disk driver name for \
                                domain \'%s\'. abort.\n\n' % (dom_name))
                sys.exit(1)

            try:
                driver_type = dom_disk_node.find('driver').get('type')
                if driver_type is None:
                    raise
                if driver_type not in \
                   self.DRIVER_TYPES[driver_name]['formats']:
                    
                    sys.stderr.write('\ndomain \'%s\' is using a unknown \
                                    disk driver type \'%s\'. abort.\n\n' \
                                    % (args.dom_name, driver_type))
                    sys.exit(1)
            except all:
                sys.stderr.write('\nfailed to get disk driver type for \
                                domain \'%s\'. abort.\n\n' % (dom_name))
                sys.exit(1)

            try:
                source_file = dom_disk_node.find('source').get('file')
                if source_file is None:
                    raise
            except all:
                sys.stderr.write('\nfailed to get disk image file name for \
                                domain \'%s\'. abort.\n\n' % (dom_name))
                sys.exit(1)

            dom_disk_infos.append(
                {
                    'xml_node': dom_disk_node,
                    'driver_name' : driver_name,
                    'driver_type' : driver_type,
                    'source_file' : source_file
                }
            )

        return dom_disk_infos

    def _get_dom_file_disk_info(self, dom_name):

        ''' Extract and return all disk definitions of type file
            for the given domain. 

        :param dom_name: name of the domain the information is requested for
        :returns: dom xml node and list of dictionaries root, [{'xml_node': 
                  <object>, 'driver_name': <string>, 'driver_type': <string>, 
                  'source_file': <string>}]
        '''

        dom = None
        try:
            dom = self._lvirt_conn.lookupByName(dom_name)
        except all:
            sys.stderr.write('\nno domain with name \'%s\' found. \
                              abort.\n\n' % (dom_name))
            sys.exit(1)

        if dom.isActive() == True:
            sys.stderr.write('\ndomain \'%s\' is running - please shutdown \
                              before converting the disk images. \
                              abort.\n\n' % (dom_name))
            sys.exit(1)

        root = None
        try:
            root = etree.fromstring(dom.XMLDesc(0))
            if root is None:
                raise
            # print etree.tostring(root)
        except all:
            sys.stderr.write('\nfailed to get XML domain description for \
                              domain \'%s\'. abort.\n\n' % (dom_name))
            sys.exit(1)

        try:
            dom_disk_nodes = root.xpath('//devices/disk[contains(@type, \
                                         "file")]')
            if len(dom_disk_nodes) == 0:
                raise
        except all:
            sys.stderr.write('\nno disk definitions of type file for \
                              domain \'%s\'. abort.\n\n' % (dom_name))
            sys.exit(1)

        return root, \
               self._get_info_from_dom_disk_nodes(dom_disk_nodes, dom_name)

    def _create_convert_tasks(self, disk_infos, destination_format, \
                             add_type_extension):
        ''' Create a convert task for each disk info.

        :param disk_infos: list of disk definitions
        :param destination_format: string containing the format 
        :return: list of task [{disk_info: <object>, destination_format: \
                 <string>}, destination_file: <string>}]
        '''

        convert_tasks = []
        for disk_info in disk_infos:

            if destination_format == disk_info['driver_type']:
                continue

            if destination_format not in \
               self.DRIVER_TYPES[disk_info['driver_name']]['formats']:
                sys.stderr.write('\ntarget format \'%s\' not supported for \
                                  disk using driver \'%s\'. abort.\n\n' \
                                  % (destination_format, \
                                     disk_info['driver_name']))
                sys.exit(1)

            source_uid = None
            source_gid = None
            try:
                source_fd = os.open(disk_info['source_file'], os.O_RDWR)
                info = os.fstat(source_fd)
                source_uid = info.st_uid
                source_gid = info.st_gid
                source_perm = info.st_mode
                os.close(source_fd)

            except IOError as err:
                sys.stderr.write('\nfailed to access file \'%s\'\n \
                                  cause:\n%s\nabort.\n\n' \
                                  % (disk_info['source_file'], err))
                sys.exit(1)

            destination_file = disk_info['source_file']
            if add_type_extension is True:
                
                destination_file = (os.path.splitext(destination_file)[0]) + \
                                    '.' + self.DRIVER_TYPES[ \
                                    disk_info['driver_name']]['formats'] \
                                    [destination_format]

            convert_tasks.append(
                {
                    'disk_info' : disk_info,
                    'destination_format' : destination_format,
                    'destination_file' : destination_file,
                    'owner_id' : source_uid,
                    'group_id' : source_gid,
                    'permissions' : source_perm,
                    'processed' : False
                }
            )

        return convert_tasks

    def __init__(self, connection_uri, dom_name, destination_format, \
                 add_type_extension = False):

        try:
            self._lvirt_conn = libvirt.open(connection_uri)
        except libvirt.libvirtError as err:
            sys.stderr.write('\nfailed to open connection to the \
                              hyper-visor cause:\n%s\n\n' % (err))
            sys.exit(1)

        self._xml_root, self._disk_infos = \
          self._get_dom_file_disk_info(dom_name)

        # print self._disk_infos

        self._convert_tasks = self._create_convert_tasks(self._disk_infos, \
                                                        destination_format, \
                                                         add_type_extension)

        # print self._convert_tasks

        self._domain = dom_name

    def __del__(self):

        try:
            self._lvirt_conn.close()
        except all:
            pass

    def get_task_num(self):
        ''' Return the number of converter tasks. 

        :returns: number of tasks
        '''

        return len(self._convert_tasks)

    def show_task_list(self):
        ''' Output the task list to stdout. '''

        for idx, task in enumerate(self._convert_tasks):
            print '%2d: [%s]:%s -> [%s]:%s' % (idx,
                                            task['disk_info']['driver_type'], 
                                            task['disk_info']['source_file'],
                                            task['destination_format'],
                                            task['destination_file'])

    def convert_all(self, show_progress_bar = False, keep_ownership=False, \
                   keep_permissions=False):
        ''' Run all present tasks. 

        :param show_progress_bar: if true, show the progress-bar generated \
               by qemu-img convert
        :param keep_ownership: keep the ownership of the source file
        :param keep_permissions: keep the file permissions of the source file
        :return: number of converted files
        '''

        idx = None
        for idx in range(len(self._convert_tasks)):
            self.convert_selected(idx, 
                                 show_progress_bar = show_progress_bar,
                                 keep_ownership = keep_ownership,
                                 keep_permissions = keep_permissions)

        return idx

    def _qemu_convert(self, source_file, source_format, destination_file, \
                      destination_format, show_progress_bar):
        ''' Convert image file using qemu-img convert.

        :param source_file: source disk image file
        :param source_format: source disk image format
        :param destination_file: destination disk image format
        :param destination_format: destination disk image format
        :param show_progress_bar: if true, show the progress-bar generated \
               by qemu-img convert
        '''

        stdout_to = subprocess.PIPE
        qemu_cmd = ['qemu-img', 
                    'convert', 
                    '-f', source_format, 
                    '-O', destination_format
                   ]
        if show_progress_bar is True:
            qemu_cmd.append('-p')
            stdout_to = None

        qemu_cmd.append(source_file)
        qemu_cmd.append(destination_file)

        try:
            if show_progress_bar is True:
                print '\nconvert image \'%s\' from format \'%s\' to \'%s\'' \
                       % (source_file, source_format, \
                       destination_format)
            
            ret = subprocess.call(qemu_cmd, stdout = stdout_to)

            if ret != 0:
                raise
        except all:
            sys.stderr.write('\nfailed to convert \'%s\' from format \'%s\' \
                              to \'%s\'. abort.\n\n' % (source_file, \
                              source_format, destination_format))
            sys.exit(1)


    def convert_selected(self, idx, show_progress_bar = False, \
                        keep_ownership=False, keep_permissions=False):
        ''' Only run task selected by id. 

        :param idx: id of the task to be run
        :param show_progress_bar: if true, show the progressbar generated \
               by qemu-img convert
        :param keep_ownership: keep the ownership of the source file
        :param keep_permissions: keep the file permissions of the source file
        '''

        try:
            task = self._convert_tasks[idx]
        except all:
            sys.stderr.write('\ninvalid task id given. abort.\n\n')
            sys.exit(1)

        # print task

        driver_name = task['disk_info']['driver_name']
        source_format = self.DRIVER_TYPES[driver_name]['formats']\
                                         [task['disk_info']['driver_type']]
        source_file = task['disk_info']['source_file']
        destination_format = self.DRIVER_TYPES[driver_name]['formats']\
                                              [task['destination_format']]
        destination_file = task['destination_file']
        xml_node = task['disk_info']['xml_node']

        try:
            ret = subprocess.call(['qemu-img', 'convert', '-h'], \
                                 stdout=subprocess.PIPE, \
                                 stderr=subprocess.PIPE)
            if  ret is not 1:
                raise
        except all:
            sys.stderr.write('\nfailed to run external tool \'qemu-img \
                              convert\'. abort.\n\n')
            sys.exit(1)

        self._qemu_convert(source_file, source_format, destination_file, \
                           destination_format, show_progress_bar)

        xml_node.find('driver').set('type', destination_format)
        xml_node.find('source').set('file', destination_file)

        if keep_ownership == True:
            try:
                os.chown(destination_file, task['owner_id'], \
                         task['group_id'])
            except IOError as err:
                sys.stderr.write('\nfailed to set ownership for file \'%s\' \
                                  cause:\n\'%s\'\nabort.\n\n' \
                                  % (destination_file, err))
                sys.exit(1)

        if keep_permissions == True:
            try:
                os.chmod(destination_file, task['permissions'])
            except IOError as err:
                sys.stderr.write('\nfailed to set permissions for file \
                                  \'%s\' cause:\n\'%s\'\nabort.\n\n' \
                                  % (destination_file, err))
                sys.exit(1)

        task['processed'] = True

        # print etree.tostring( task['disk_info']['xml_node'])

    def commit_changes(self, remove_old_files = False):
        ''' Update the machine configuration and delete old files if \
            requested. 

        :param remove_old_files: if True, old files are deleted
        '''

        self._lvirt_conn.defineXML(etree.tostring(self._xml_root))

        if remove_old_files == True:
            for task in self._convert_tasks:
                if task['processed'] == True:
                    os.remove (task['disk_info']['source_file'])

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--libvirt-connection-uri', \
                   default='qemu:///system', help='URI to connectd to \
                   (default: /etc/libvirt)')
    parser.add_argument('-f', '--output-format', default='qcow2', help='target \
                   format (default: qcow2)')
    parser.add_argument('-n', '--dom-name', required=True, help='name of the \
                   domain the disks should be converted for')
    parser.add_argument('-x', '--add-type-extension', action='store_true', \
                   default=False, help='add type of the image as file \
                   extension to the image file name (default: false)')
    parser.add_argument('-p', '--show-progress-bar', action='store_true', \
                   default=False, help='show progress bar while convert is \
                   running (default: false) ')
    parser.add_argument('-r', '--remove-old-files', action='store_true', \
                   default=False, help='remove old files after all \
                   translations succeeded (default: false)')
    parser.add_argument('-o', '--keep-file-ownership', action='store_true', \
                   default=False, help='keep owner and group of the file \
                   (default: false)')
    parser.add_argument('-k', '--keep-file-permissions', action='store_true', \
                   default=False, help='apply file permissions of the \
                   source file (default: false)')

    args = parser.parse_args()

    converter = LibVirtDriveConvert(args.libvirt_connection_uri, \
                                    args.dom_name, \
                                    args.output_format, \
                                    add_type_extension = \
                                                  args.add_type_extension)

    converter.show_task_list()

    converter.convert_all(show_progress_bar = args.show_progress_bar, \
                          keep_ownership = args.keep_file_ownership, \
                          keep_permissions = args.keep_file_permissions)

    converter.commit_changes(remove_old_files = args.remove_old_files)
