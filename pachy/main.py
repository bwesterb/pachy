#!/usr/bin/env python
# vim: et:sta:bs=2:sw=4:

# pachy (short for pachyderm referring to elephants) is a backup tool.
#
# Bas Westerbaan <bas@westerbaan.name>
# Licensed under the GPLv3

import sys
import shlex
import logging
import os.path
import argparse
import datetime
import subprocess

class Pachy(object):
    def parse_cmdLine_args(self):
        parser = argparse.ArgumentParser(
                        description='pachy does incremental backups')
        parser.add_argument('source', metavar='SRC',
                                help='source directory')
        parser.add_argument('dest', metavar='DEST',
                                help='destination directory')

        parser.add_argument('--tar', default='tar', metavar='CMD',
                help='The tar compatible archiver to use.')
        parser.add_argument('--compressor', default='xz -9', metavar='CMD',
                help='The xz compatible compressor to use. '+
                     'eg: `gz -5\'')
        parser.add_argument('--differ', default='xdelta3', metavar='CMD',
                help='The xdelta3 compatible differ to use')
        parser.add_argument('--rsync', default='rsync -v', metavar='CMD',
                help='The rsync command to use. '+
                     'eg: `rsync -e "ssh -p 123"\'')
        parser.add_argument('--steps', default='01234',
                help='Specifies which steps to perform. Default is `01234\'. '+
                        'Only use for debugging.')
        self.args = parser.parse_args()
        # Ensure source has a trailing /
        self.source_arg = self.args.source
        if not self.source_arg.endswith('/'):
            self.source_arg += '/'
        # Set some convenience variables
        self.mirror_dir = os.path.abspath(os.path.join(
                                self.args.dest, 'mirror'))
        self.deltas_dir = os.path.abspath(os.path.join(
                                self.args.dest, 'deltas'))
        self.work_dir = os.path.abspath(os.path.join(
                                self.args.dest, 'work'))
        self.pile_dir = os.path.join(self.work_dir, 'pile')

    def main(self):
        self.parse_cmdLine_args()
        if '0' in self.args.steps:
            logging.info("0. Checking set-up")
            self.check_setup()
        if '1' in self.args.steps:
            logging.info("1. Running rsync")
            self.run_rsync()
        if '2' in self.args.steps:
            logging.info("2. Checking for changes")
            self.find_changed()
        if '3' in self.args.steps:
            logging.info("3. Creating archive")
            self.create_archive()
        if '4' in self.args.steps:
            logging.info("4. Cleaning up")
            self.cleanup()

    def check_setup(self):
        # Does the destination directory exist?
        if not os.path.exists(self.args.dest):
            # TODO add an option to create the directory
            logging.error('Destination directory does not exist')
            sys.exit(1)
        # Do the mirror, deltas and work subdirectories exist?
        for d in (self.mirror_dir, self.deltas_dir, self.work_dir):
            if not os.path.exists(d):
                os.mkdir(d)
        # Is the work directory empty?
        if os.listdir(self.work_dir):
            # TODO add an option to clean the directory
            logging.error('The work directory is not empty')
            sys.exit(2)
        os.mkdir(os.path.join(self.work_dir, 'pile'))
        os.mkdir(os.path.join(self.work_dir, 'changed'))
        os.mkdir(os.path.join(self.work_dir, 'deleted'))
        
    def run_rsync(self):
        ret = subprocess.call(
                shlex.split(self.args.rsync) +
                        ['--archive', # we want to preserve metadata
                         '--backup',  # do not override files
                         '--delete',  # delete extraneous files
                         self.source_arg,
                         self.mirror_dir,
                         '--backup-dir='+self.pile_dir,
                         '--filter=dir-merge /.pachy-filter'])
        if ret != 0:
            logging.error('rsync failed with error code %s', ret)
            sys.exit(3)

    def find_changed(self):
        # walk the work directory
        stack = ['.']
        while stack:
            d = stack.pop()
            d_pile = os.path.join(self.pile_dir, d)
            d_mirror = os.path.join(self.mirror_dir, d)
            for c in os.listdir(d_pile):
                c_pile = os.path.join(d_pile, c)
                if os.path.isdir(c_pile):
                    stack.append(os.path.join(d, c))
                    continue
                c_mirror = os.path.join(d_mirror, c)
                # c is a file in the work directory.
                if not os.path.exists(c_mirror):
                    # it was apparently deleted. Move to deleted.
                    d_deleted = os.path.join(self.work_dir, 'deleted', d)
                    # TODO cache this to limit syscalls
                    if not os.path.exists(d_deleted):
                        os.makedirs(d_deleted)
                    os.rename(c_pile, os.path.join(d_deleted, c))
                    continue
                # c was changed.  Create a xdelta
                d_changed = os.path.join(self.work_dir, 'changed', d)
                # TODO cache this to limit syscalls
                if not os.path.exists(d_changed):
                    os.makedirs(d_changed)
                self.create_delta(os.path.join(d, c))

    def create_delta(self, f):
        f_pile = os.path.join(self.pile_dir, f)
        f_mirror = os.path.join(self.mirror_dir, f)
        f_changed = os.path.join(self.work_dir, 'changed', f) + '.xdelta3'
        ret = subprocess.call(
                   shlex.split(self.args.differ) +
                   ['-s', f_pile, # source
                    f_mirror,     # target
                    f_changed])   # out
        if ret != 0:
            logging.error('xdelta3 failed with errorcode %s', ret)
            sys.exit(4)

    def create_archive(self):
        if (not os.listdir(os.path.join(self.work_dir, 'changed')) and
                not os.listdir(os.path.join(self.work_dir, 'deleted'))):
            logging.info("No changes.  Will not create archive.")
            return
        archive_path = os.path.join(self.deltas_dir,
                    datetime.datetime.now().strftime('%Y-%m-%d@%Hh%M.%S.tar'))
        ret = subprocess.call(
                   shlex.split(self.args.tar) +
                   ['-cf',        # create a file
                    archive_path,
                    'changed',
                    'deleted'],
                        cwd=self.work_dir)
        if ret != 0:
            logging.error('tar failed with errorcode %s', ret)
            sys.exit(5)
        ret = subprocess.call(
                   shlex.split(self.args.compressor) +
                   [archive_path])
        if ret != 0:
            logging.error('xz failed with errorcode %s', ret)
            sys.exit(6)
    def cleanup(self):
        ret = subprocess.call([
                    'rm',
                    '-r',
                    self.work_dir])
        if ret != 0:
            logging.error('rm failed with errorcode %s', ret)
            sys.exit(7)

def main():
    logging.basicConfig(level=logging.DEBUG)
    Pachy().main()

if __name__ == '__main__':
    main()
