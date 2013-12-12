import ConfigParser
import hashlib
import StringIO
import sys
import unittest
import zipfile

import os.path as op

import mock

from egginst import exe_data

from egginst.main import EggInst
from egginst.scripts import create, create_proxies, fix_script, get_executable
from enstaller.utils import md5_file

from .common import mkdtemp

DUMMY_EGG_WITH_PROXY = op.join(op.dirname(__file__), "data", "dummy_with_proxy-1.3.40-3.egg")
DUMMY_EGG_WITH_PROXY_SCRIPTS = op.join(op.dirname(__file__), "data", "dummy_with_proxy_scripts-1.0.0-1.egg")

class TestScripts(unittest.TestCase):
    def test_get_executable(self):
        # FIXME: EggInst init overwrite egginst.scripts.executable. Need to
        # mock this until we remove that insanity
        with mock.patch("egginst.scripts.executable", sys.executable):
            executable = get_executable()
            self.assertEqual(executable, sys.executable)

            executable = get_executable(with_quotes=True)
            self.assertEqual(executable, "\"{0}\"".format(sys.executable))

        with mock.patch("egginst.scripts.on_win", "win32"):
            with mock.patch("egginst.scripts.executable", "python.exe"):
                executable = get_executable()
                self.assertEqual(executable, "python.exe")

            with mock.patch("egginst.scripts.executable", "pythonw.exe"):
                executable = get_executable()
                self.assertEqual(executable, "python.exe")

                executable = get_executable(pythonw=True)
                self.assertEqual(executable, "pythonw.exe")

class TestFixScript(unittest.TestCase):
    def test_egginst_script_untouched(self):
        """
        Ensure we don't touch a script which has already been written by
        egginst.
        """
        simple_script = """\
#!/home/davidc/src/enthought/enstaller/.env/bin/python
# This script was created by egginst when installing:
#
#   enstaller-4.6.3.dev1-py2.7.egg
#
if __name__ == '__main__':
    import sys
    from enstaller.patch import main

    sys.exit(main())
"""

        with mkdtemp() as d:
            path = op.join(d, "script")
            with open(path, "wt") as fp:
                fp.write(simple_script)

            fix_script(path)

            with open(path, "rt") as fp:
                self.assertEqual(fp.read(), simple_script)

    @mock.patch("egginst.scripts.executable", sys.executable)
    def test_setuptools_script_fixed(self):
        """
        Ensure a script generated by setuptools is fixed.
        """
        setuptools_script = """\
#!/dummy_path/.env/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'enstaller==4.6.3.dev1','console_scripts','enpkg'
__requires__ = 'enstaller==4.6.3.dev1'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('enstaller==4.6.3.dev1', 'console_scripts', 'enpkg')()
    )
"""
        r_egginst_script = """\
#!{prefix}
# EASY-INSTALL-ENTRY-SCRIPT: 'enstaller==4.6.3.dev1','console_scripts','enpkg'
__requires__ = 'enstaller==4.6.3.dev1'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('enstaller==4.6.3.dev1', 'console_scripts', 'enpkg')()
    )
""".format(prefix=sys.executable)

        with mkdtemp() as d:
            path = op.join(d, "script")
            with open(path, "wt") as fp:
                fp.write(setuptools_script)

            fix_script(path)

            with open(path, "rt") as fp:
                self.assertEqual(fp.read(), r_egginst_script)

class TestCreateScript(unittest.TestCase):
    @mock.patch("egginst.utils.on_win", False)
    def test_simple(self):
        r_cli_entry_point = """\
#!{executable}
# This script was created by egginst when installing:
#
#   dummy.egg
#
if __name__ == '__main__':
    import sys
    from dummy import main_cli

    sys.exit(main_cli())
""".format(executable=sys.executable)

        entry_points = """\
[console_scripts]
dummy = dummy:main_cli

[gui_scripts]
dummy-gui = dummy:main_gui
"""
        s = StringIO.StringIO(entry_points)
        config = ConfigParser.ConfigParser()
        config.readfp(s)

        with mkdtemp() as d:
            egginst = EggInst("dummy.egg", d)
            create(egginst, config)

            entry_point = op.join(egginst.bin_dir, "dummy")
            self.assertTrue(op.exists(entry_point))

            with open(entry_point, "rt") as fp:
                cli_entry_point = fp.read()
                self.assertMultiLineEqual(cli_entry_point, r_cli_entry_point)

    @mock.patch("egginst.scripts.on_win", True)
    @mock.patch("egginst.main.bin_dir_name", "Scripts")
    def test_simple_windows(self):
        python_executable = "C:\\Python27\\python.exe"
        pythonw_executable = "C:\\Python27\\pythonw.exe"

        r_cli_entry_point = """\
#!"{executable}"
# This script was created by egginst when installing:
#
#   dummy.egg
#
if __name__ == '__main__':
    import sys
    from dummy import main_cli

    sys.exit(main_cli())
""".format(executable=python_executable)

        r_gui_entry_point = """\
#!"{executable}"
# This script was created by egginst when installing:
#
#   dummy.egg
#
if __name__ == '__main__':
    import sys
    from dummy import main_gui

    sys.exit(main_gui())
""".format(executable=pythonw_executable)

        entry_points = """\
[console_scripts]
dummy = dummy:main_cli

[gui_scripts]
dummy-gui = dummy:main_gui
"""
        s = StringIO.StringIO(entry_points)
        config = ConfigParser.ConfigParser()
        config.readfp(s)

        with mock.patch("sys.executable", python_executable):
            with mkdtemp() as d:
                egginst = EggInst("dummy.egg", d)
                create(egginst, config)

                cli_entry_point_path = op.join(egginst.bin_dir, "dummy-script.py")
                gui_entry_point_path = op.join(egginst.bin_dir, "dummy-gui-script.pyw")
                entry_points = [
                        op.join(egginst.bin_dir, "dummy.exe"),
                        op.join(egginst.bin_dir, "dummy-gui.exe"),
                        cli_entry_point_path, gui_entry_point_path,
                ]
                for entry_point in entry_points:
                    self.assertTrue(op.exists(entry_point))

                with open(cli_entry_point_path, "rt") as fp:
                    cli_entry_point = fp.read()
                    self.assertMultiLineEqual(cli_entry_point, r_cli_entry_point)

                with open(gui_entry_point_path, "rt") as fp:
                    gui_entry_point = fp.read()
                    self.assertMultiLineEqual(gui_entry_point, r_gui_entry_point)

                self.assertEqual(md5_file(op.join(egginst.bin_dir, "dummy.exe")),
                                 hashlib.md5(exe_data.cli).hexdigest())
                self.assertEqual(md5_file(op.join(egginst.bin_dir, "dummy-gui.exe")),
                                 hashlib.md5(exe_data.gui).hexdigest())

class TestProxy(unittest.TestCase):
    @mock.patch("sys.platform", "win32")
    @mock.patch("egginst.main.bin_dir_name", "Scripts")
    @mock.patch("egginst.utils.on_win", True)
    def test_proxy(self):
        """
        Test we handle correctly entries of the form 'path PROXY'.
        """
        r_python_proxy_data_template = """\
#!"{executable}"
# This proxy was created by egginst from an egg with special instructions
#
import sys
import subprocess

src = '{prefix}/EGG-INFO/dummy_with_proxy/usr/swig.exe'

sys.exit(subprocess.call([src] + sys.argv[1:]))
"""

        with mkdtemp() as prefix:
            with mock.patch("sys.executable", op.join(prefix, "python.exe")):
                r_python_proxy_data = r_python_proxy_data_template.format(
                        executable=op.join(prefix, "python.exe"),
                        prefix=prefix)

                egginst = EggInst(DUMMY_EGG_WITH_PROXY, prefix)
                with zipfile.ZipFile(egginst.path) as zp:
                    egginst.z = zp
                    egginst.arcnames = zp.namelist()
                    create_proxies(egginst)

                    python_proxy = op.join(prefix, "Scripts", "swig-script.py")
                    coff_proxy = op.join(prefix, "Scripts", "swig.exe")

                    self.assertTrue(op.exists(python_proxy))
                    self.assertTrue(op.exists(coff_proxy))

                    self.assertTrue(md5_file(coff_proxy),
                                    hashlib.md5(exe_data.cli).hexdigest())

                    with open(python_proxy) as fp:
                        python_proxy_data = fp.read()
                        self.assertMultiLineEqual(
                                python_proxy_data,
                                r_python_proxy_data)

    @mock.patch("sys.platform", "win32")
    @mock.patch("egginst.main.bin_dir_name", "Scripts")
    @mock.patch("egginst.utils.on_win", True)
    def test_proxy_directory(self):
        """
        Test we handle correctly entries of the form 'path some_directory'.
        """
        with mkdtemp() as prefix:
            with mock.patch("sys.executable", op.join(prefix, "python.exe")):
                egginst = EggInst(DUMMY_EGG_WITH_PROXY_SCRIPTS, prefix)
                with zipfile.ZipFile(egginst.path) as zp:
                    egginst.z = zp
                    egginst.arcnames = zp.namelist()
                    create_proxies(egginst)

                    proxied_files = [
                       op.join(prefix, "Scripts", "dummy.dll"),
                       op.join(prefix, "Scripts", "dummy.lib"),
                    ]
                    for proxied_file in proxied_files:
                        self.assertTrue(op.exists(proxied_file))
