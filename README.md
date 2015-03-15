# libvirt-drive-convert

A simple command line tool to convert disk images used by libvirt domains.

Basic behavior:
- convert all disk image files related to given domain
- adapt the domain configuration to use the new image
- only convert file if needed (eg. don't convert cow to cow)
- delete old files if requested
- keep ownership and file permissions if requested
- on error: keep original configuration

Example usage - convert disk image used by domain debian-master to qcow2, 
keep ownership and file mode, delete old file after conversion was finished
without errors.
```
#> python libvirt_drive_convert.py --dom-name=debian-master --output-format=qcow2 -x -p -r -o -k 
```

# help

```
usage: libvirt_drive_convert.py [-h] [-u LIBVIRT_CONNECTION_URI]
                                [-f OUTPUT_FORMAT] -n DOM_NAME [-x] [-p] [-r]
                                [-o] [-k]

optional arguments:
  -h, --help            show this help message and exit
  -u LIBVIRT_CONNECTION_URI, --libvirt-connection-uri LIBVIRT_CONNECTION_URI
                        URI to connectd to (default: /etc/libvirt)
  -f OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
                        target format (default: qcow2)
  -n DOM_NAME, --dom-name DOM_NAME
                        name of the domain the disks should be converted for
  -x, --add-type-extension
                        add type of the image as file extension to the image
                        file name (default: false)
  -p, --show-progress-bar
                        show progress bar while convert is running (default:
                        false)
  -r, --remove-old-files
                        remove old files after all translations succeeded
                        (default: false)
  -o, --keep-file-ownership
                        keep owner and group of the file (default: false)
  -k, --keep-file-permissions
                        apply file permissions of the source file (default:
                        false)
```
