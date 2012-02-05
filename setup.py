#!/usr/bin/env python
# vim: et:sta:bs=2:sw=4:

from setuptools import setup
from get_git_version import get_git_version

setup(name='pachy',
      version=get_git_version(),
      description='Simple incremental backups with rsync and xdelta3',
      author='Bas Westerbaan',
      author_email='bas@westerbaan.name',
      url='http://github.com/bwesterb/pachy/',
      packages=['pachy'],
      zip_safe=True,
      install_requires = ['docutils>=0.3'],
      entry_points = {
          'console_scripts': [
              'pachy = pachy.main:main',
              ]
          },
      classifiers=[
              "Topic :: System :: Archiving :: Backup",
              "License :: OSI Approved :: GNU General Public License (GPL)",
              "Development Status :: 4 - Beta"])
