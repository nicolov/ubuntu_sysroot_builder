#!/usr/bin/env python

"""
Get URLs for .deb files listed in package.list, and save them in
packages.lock.
"""

from __future__ import print_function

from collections import defaultdict
import gzip
import json
from io import BytesIO
import os
import pickle
import requests
import shutil
import subprocess


apt_sources = [
    "http://mirrors.sonic.net/ubuntu/ trusty main universe",
    "http://mirrors.sonic.net/ubuntu/ trusty-updates main universe",
]


def version_compare(ver_a, ver_b):
    """Return > 0 if ver_a > ver_b."""
    def make_call(op):
        return subprocess.call(['dpkg', '--compare-versions', ver_a, op, ver_b])

    if make_call('eq') == 0:
        return 0
    else:
        return 1 if make_call('gt') == 0 else -1

assert version_compare('0.2', '0.1') == 1
assert version_compare('0.1', '0.2') == -1


def parse_packages(lines, repo_url):
    """Parse the contents of a Packages file, given as a list of strings,
    one for each line in the file.
    Returns: a list of dictionaries, one for each package in the repo."""

    pkgs = defaultdict(list)
    current_pkg = {}

    for l in lines:
        # Empty lines delimit package stanzas.
        if not l:
            assert current_pkg
            assert 'Package' in current_pkg
            current_pkg['_RepoUrl'] = repo_url
            pkgs[current_pkg['Package']].append(current_pkg)
            current_pkg = {}
            continue

        try:
            key, value = l.split(": ", 1)
        except:
            # TODO(nico): support line continuations?
            continue

        # Store the current key/value pair
        if key in ('Package', 'Version', 'Filename', 'SHA256'):
            current_pkg[key] = value

    return pkgs


CACHE_PATH = 'packages.pickle'


def build_packages_cache():
    packages_data = {}

    for apt_source_line in apt_sources:
        repo_url, distro, components = apt_source_line.split(' ', 2)
        components = components.split(' ')
        for component in components:
            list_url = "{repo_url}dists/{distro}/{component}/binary-amd64/Packages.gz".format(
                repo_url=repo_url, distro=distro, component=component)

            print('Downloading {}'.format(list_url))
            r = requests.get(list_url)
            r.raise_for_status()

            buf = BytesIO(r.content)
            gzipfile = gzip.GzipFile(fileobj=buf)
            content_lines = [l.rstrip('\r\n') for l in gzipfile.readlines()]

            packages_data[list_url] = parse_packages(content_lines, repo_url)
    return packages_data


def main():
    # Merging the package lists is slow, so we cache it
    if not os.path.exists(CACHE_PATH):
        print('Rebuilding cache in {}'.format(CACHE_PATH))
        packages_data = build_packages_cache()
        with open(CACHE_PATH, 'wb') as f:
            pickle.dump(packages_data, f)
    else:
        print('Using cached packages from {}'.format(CACHE_PATH))
        packages_data = pickle.load(open(CACHE_PATH, 'rb'))

    print('{} repositories in cache'.format(len(packages_data)))

    # Now go through the list of required packages and write out the URLs to
    # the .debs
    with open('packages.list') as f:
        package_lines = [l.strip() for l in f.readlines()
                         if l.strip() and not l.startswith('#')]

    # Validate that packages are mentioned with multiple pinned versions, and
    # make sure that pins have precedence over non-pinned packages.
    packages_with_pins = {}
    for pl in package_lines:
        split_line = pl.split('=')
        if len(split_line) == 2:  # pinned package
            # Validate that there is no previous pin
            assert packages_with_pins.get(split_line[0]) is None, \
                "Package '{}' is already pinned".format(split_line[0])
            packages_with_pins[split_line[0]] = split_line[1]
        else:  # non-pinned package
            # Don't overwrite a previous pin
            if not split_line[0] in packages_with_pins:
                packages_with_pins[split_line[0]] = None

    # Decide which repo to get each each package from
    deb_urls = []
    for req_pkg in sorted(packages_with_pins):
        # sum([[..],..], ..) flattens the list of packages from each repo
        candidates = sum([
            repo_packages[req_pkg]
            for repo_packages in packages_data.values()
            if req_pkg in repo_packages
        ], [])

        assert candidates, \
            "Requested package '{}' not found".format(req_pkg)

        req_version = packages_with_pins[req_pkg]
        if req_version:
            sorted_candidates = [
                c for c in candidates if c['Version'] == req_version]
            assert sorted_candidates, \
                "Failed to find pinned version '{}' for '{}'. Available versions: {}".format(
                    req_version, req_pkg, [c['Version'] for c in candidates])
        else:
            sorted_candidates = sorted(
                candidates,
                cmp=lambda c1, c2: version_compare(c2['Version'], c1['Version']))

        best_pkg = sorted_candidates[0]
        deb_urls.append(best_pkg['_RepoUrl'] + best_pkg['Filename'])

    with open('packages.lock', 'w') as f:
        json.dump(deb_urls, f, indent=2)


if __name__ == "__main__":
    main()
