pachy
=====

*pachy* is a simple Python script to create *incremental* backups using
*rsync* and *xdelta3*:

- By using *rsync* backups require **little bandwidth**;
- By using *xdelta3*, incremental backups use **little space**;
- The codebase is very small; thus **easy to adapt** to your own needs.

Getting started
---------------
### Installing *pachy*

You will need Python's
[setuptools](http://pypi.python.org/pypi/setuptools);
[xz-utils](http://tukaani.org/xz/)
[rsync](http://rsync.net/) and
[xdelta3](http://xdelta.org/).
On Debian Linux, execute:

    $ apt-get install python-setuptools rsync xdelta3 xz-utils

Then, to install *pachy*:

    $ easy_install pachy

### Example: local backups
In this example we will backup our `~/Document` folder that contains:

    .
    ├── dir1
    │   ├── document2
    │   └── document3
    └── example1

#### First backup
To create a backup of `~/Documents` to `/mnt/disk/Backup`, execute:

    $ pachy ~/Documents /mnt/disk/Backup
    INFO:root:0. Checking set-up
    INFO:root:1. Running rsync
    sending incremental file list
    ./
    example1
    dir1/
    dir1/document2
    dir1/document3
    
    sent 237 bytes  received 76 bytes  626.00 bytes/sec
    total size is 0  speedup is 0.00
    INFO:root:2. Checking for changes
    INFO:root:3. Creating archive
    INFO:root:4. Cleaning up

#### Incremental backups
After some work we changed the file `example1` and deleted `document2`.
To create an incremental backup, just run the same command a second time.
Only changes will be copied.

    $ pachy ~/Documents /mnt/disk/Backup
    INFO:root:0. Checking set-up
    INFO:root:1. Running rsync
    sending incremental file list
    ./
    example1
    dir1/
    deleting dir1/document2
    
    sent 161 bytes  received 38 bytes  398.00 bytes/sec
    total size is 9  speedup is 0.05
    INFO:root:2. Checking for changes
    INFO:root:3. Creating archive
    INFO:root:4. Cleaning up

#### Backup format
If you look at `/mnt/disk/Backup` you will find it contains:

    .
    ├── deltas
    │   └── 2012-02-05@14h13.02.tar.xz
    └── mirror
        ├── dir1
        │   └── document3
        └── example1

The `mirror` subdirectory is an exact copy of the `~/Documents` folder.
Under `deltas` there is for each incremental backup a `.tar.xz` archive.
We can uncompress it with

    $ tar xJf 2012-02-05@14h13.02.tar.xz

We see it contains:

    .
    ├── changed
    │   └── example1.xdelta3
    └── deleted
        └── dir1
            └── document2

Under the `deleted` folder are all the files that were deleted.
Under `changed` are the *xdelta3* differences of the changed file.

To restore the old `example1` to `example1.restored`, run:

    $ xdelta3 -d -s example1 example1.xdelta3 example1.restored

### Example: backing up a server via rsync over SSH
To create daily backups of a full server, execute:

    $ crontab -e

and add the following line

    @daily pachy my-server.com:/ /backups/my-server

This will create a full backup of **all** files.  If you want to exclude
some files, you can create a `.pachy-filter` file in the root of the
server with:

    - /proc
    - /dev
    - /sys
    - /tmp
    - /var/tmp
    - /var/run
    - /var/cache
