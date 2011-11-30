import os
import sys
from os.path import isdir, isfile, join

import egginst
from egginst.utils import pprint_fn_action, console_progress

from plat import custom_plat
from utils import stream_to_file, md5_file



class Resource(object):

    def __init__(self, repo, prefix=sys.prefix, plat=custom_plat,
                 verbose=False):
        self.repo = repo
        self.prefix = prefix
        self.plat = custom_plat
        self.verbose = verbose

        self.progress_callback = console_progress
        self.action_callback = pprint_fn_action

        self.fetch_dir = join(prefix, 'LOCAL-REPO')
        self.pkgs_dir = join(prefix, 'pkgs')

    def launch_app(self, egg):
        pass

    def install(self, egg, force=False, hook=True):
        if not force and hook and isfile(self.registry_path_egg(egg)):
            if self.verbose:
                print "Already installed:", egg
            return
        egg_path = join(self.fetch_dir, egg)
        if not isfile(egg_path):
            self.fetch_egg(egg, force)
        self.action_callback(egg, 'installing')
        ei = egginst.EggInst(egg_path, prefix=self.prefix, hook=hook,
                             pkgs_dir=self.pkgs_dir, verbose=self.verbose)
        ei.progress_callback = self.progress_callback
        ei.install()

    def remove(self, egg, hook=True):
        self.action_callback(egg, 'removing')
        ei = egginst.EggInst(egg, prefix=self.prefix, hook=hook,
                             pkgs_dir=self.pkgs_dir, verbose=self.verbose)
        ei.progress_callback = self.progress_callback
        ei.remove()

    def registry_path_egg(self, egg):
        return join(self.versioned_dir_egg(egg), 'EGG-INFO', 'registry.txt')

    def versioned_dir_egg(self, egg):
        return join(self.pkgs_dir, egg[:-4])

    def patch_egg(self, egg):
        """
        Try to create 'egg' by patching an already existing egg, returns
        True on success and False on failure, i.e. when either:
            - bsdiff4 is not installed
            - no patches can be applied because: (i) there are no relevant
              patches in the repo (ii) a source egg is missing
        """
        try:
            import enstaller.zdiff as zdiff
        except ImportError:
            if self.verbose:
                print "Warning: could not import bsdiff4, cannot patch"
            return False

        possible = []
        for patch_fn, info in self.repo.query(type='patch',
                                              name=egg.split('-')[0].lower(),
                                              dst=egg):
            print patch_fn
            assert info['dst'] == egg
            src_path = join(self.fetch_dir, info['src'])
            #print '%8d %s %s' % (info['size'], patch_fn, isfile(src_path))
            if isfile(src_path):
                possible.append((info['size'], patch_fn, info))

        if not possible:
            return False
        size, patch_fn, info = min(possible)

        self.action_callback(patch_fn, 'fetching')
        patch_path = join(self.fetch_dir, patch_fn)
        stream_to_file(self.repo.get(patch_fn), patch_path,
                       info, self.progress_callback)

        self.action_callback(info['src'], 'patching')
        zdiff.patch(join(self.fetch_dir, info['src']),
                    join(self.fetch_dir, egg), patch_path,
                    self.progress_callback)
        return True

    def fetch_egg(self, egg, force=False):
        """
        fetch an egg, i.e. copy or download the distribution into
        self.fetch_dir.
        force: force download or copy if MD5 mismatches
        """
        if not isdir(self.fetch_dir):
            os.makedirs(self.fetch_dir)
        info = self.repo.get_metadata(egg)
        path = join(self.fetch_dir, egg)

        # if force is used, make sure the md5 is the expected, otherwise
        # merely see if the file exists
        if isfile(path):
            if force:
                if md5_file(path) == info.get('md5'):
                    if self.verbose:
                        print "Not refetching, %r MD5 match" % path
                    return
            else:
                if self.verbose:
                    print "Not forcing refetch, %r exists" % path
                return

        if not force and self.patch_egg(egg):
            return

        self.action_callback(egg, 'fetching')
        stream_to_file(self.repo.get(egg), path, info,
                       self.progress_callback)


if __name__ == '__main__':
    from repo.indexed import LocalIndexedRepo
    from repo.chained import ChainedRepo

    r = ChainedRepo([LocalIndexedRepo('/Users/ischnell/repo'),
                     LocalIndexedRepo('/Users/ischnell/repo2')])
    #r = LocalIndexedRepo('/Users/ischnell/repo/')
    r.connect()
    x = Resource(r, prefix='/Users/ischnell/jpm/Python-2.7.2-1',
                 verbose=1)
    x.install('enstaller-4.5.0-1.egg')
    x.remove('enstaller-4.5.0-1.egg')
