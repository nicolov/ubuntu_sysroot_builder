#!/usr/bin/env python

"""
Download and unpack .deb files listed in packages.lock. Also makes sure
that symlinks in the sysroot are relative.
"""

import json
import os
import re
import subprocess


def main():
    deb_urls = json.load(open('packages.lock'))

    try:
        os.makedirs('debs')
    except OSError:
        pass

    # Download packages
    aria_input = []
    for url in deb_urls:
        aria_input += [
            url,
            '  out=' + os.path.basename(url)]

    subprocess.Popen([
        "aria2c",
        "--summary-interval=0",
        "-j8",
        "--auto-file-renaming=false",
        "--allow-overwrite=false",
        "--force-save",
        "-i", "-",
    ], stdin=subprocess.PIPE, cwd='debs').communicate(
        input='\n'.join(aria_input))

    # A debian/ directory and control file are needed to run dpkg-shlibdeps
    subprocess.check_call(
        'rm -rf root && mkdir -p root/debian && touch root/debian/control', shell=True)

    for url in deb_urls:
        deb_path = os.path.join('debs', os.path.basename(url))
        print('Extracting {}'.format(deb_path))
        subprocess.check_call([
            'dpkg-deb', '-x', deb_path, 'root'])

    # Prune /usr/share
    subprocess.check_call('rm -rf root/usr/share*', shell=True)

    # Cleanup symlinks (CleanupJailSymlinks in the chromium sysroot scripts)
    libdirs = ["lib", "lib64", "usr/lib"]

    links_and_targets = subprocess.check_output(
        ['find'] + libdirs + ['-type', 'l', '-printf', '%p\n%l\n'],
        cwd='root').rstrip('\n').split('\n')

    for link, target in zip(links_and_targets, links_and_targets[1:])[::2]:
        # Skip links with non-absolute paths
        if not target.startswith('/'):
            continue
        # Relativize the symlink
        print('Relativizing symlink {} -> {}'.format(link, target))
        prefix = re.sub('[^/]', '', link).replace('/', '../')
        subprocess.check_call(
            ['ln', '-snfv', '{}{}'.format(prefix, target), link], cwd='root')

    # Sanity check
    # links = subprocess.check_output(
    #     ['find'] + libdirs + ['-type', 'l', '-printf', '%p\n'],
    #     cwd='root').rstrip('\n').split('\n')
    # for l in links:
    #     if not os.path.exists(l):
    #         raise Exception("Found bad link:", l)

    # Rewrite absolute paths in linker scripts
    linker_scripts = [
        "root/usr/lib/x86_64-linux-gnu/libpthread.so",
        "root/usr/lib/x86_64-linux-gnu/libc.so"]

    subprocess.check_call(
        ['sed', '-i', '-e', 's|/usr/lib/x86_64-linux-gnu/||g'] + linker_scripts)
    subprocess.check_call(
        ['sed', '-i', '-e', 's|/lib/x86_64-linux-gnu/||g'] + linker_scripts)


if __name__ == '__main__':
    main()
