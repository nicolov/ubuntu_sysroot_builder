#!/usr/bin/env python

"""
Pack the sysroot into a .tar.xz, tagged with the current git revision.
"""

import subprocess

if __name__ == '__main__':
    git_tag = subprocess.check_output([
        'git', 'describe', '--always', '--dirty']).strip()
    if git_tag.endswith('dirty'):
        raise Exception("Trying to create a package with uncommitted changes")

    out_filename = 'ubuntu-sysroot-{}.tar.xz'.format(git_tag)
    print(out_filename)

    subprocess.check_call(['rm', '-f', out_filename])
    subprocess.check_call([
        'tar', '-I', 'pxz', '-cf', out_filename, 'root'])
