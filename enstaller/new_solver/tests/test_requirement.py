from egginst.vendor.six.moves import unittest

from enstaller.errors import EnstallerException, SolverException
from enstaller.versions.enpkg import EnpkgVersion

from ..constraint import MultiConstraints
from ..constraint_types import Any, EnpkgUpstreamMatch, Equal
from ..requirement import Requirement, parse_package_full_name


V = EnpkgVersion.from_string


class TestRequirement(unittest.TestCase):
    def test_comparison(self):
        # Given
        requirement_string1 = "numpy >= 1.8.1-3, numpy < 1.9.0"
        requirement_string2 = "numpy >= 1.8.1-3, numpy < 1.9.1"

        # When
        requirement1 = Requirement._from_string(requirement_string1)
        requirement2 = Requirement._from_string(requirement_string2)

        # Then
        self.assertTrue(requirement1 != requirement2)

    def test_hashing(self):
        # Given
        requirement_string = "numpy >= 1.8.1-3, numpy < 1.9.0"

        # When
        requirement1 = Requirement._from_string(requirement_string)
        requirement2 = Requirement._from_string(requirement_string)

        # Then
        self.assertEqual(requirement1, requirement2)
        self.assertEqual(hash(requirement1), hash(requirement2))

    def test_any(self):
        # Given
        requirement_string = "numpy"

        # When
        requirement = Requirement._from_string(requirement_string)

        # Then
        self.assertTrue(requirement.matches(V("1.8.1-2")))
        self.assertTrue(requirement.matches(V("1.8.1-3")))
        self.assertTrue(requirement.matches(V("1.8.2-1")))
        self.assertTrue(requirement.matches(V("1.9.0-1")))

    def test_simple(self):
        # Given
        requirement_string = "numpy >= 1.8.1-3, numpy < 1.9.0"

        # When
        requirement = Requirement._from_string(requirement_string)

        # Then
        self.assertFalse(requirement.matches(V("1.8.1-2")))
        self.assertTrue(requirement.matches(V("1.8.1-3")))
        self.assertTrue(requirement.matches(V("1.8.2-1")))
        self.assertFalse(requirement.matches(V("1.9.0-1")))

    def test_multiple_fails(self):
        # Given
        requirement_string = "numpy >= 1.8.1-3, scipy < 1.9.0"

        # When
        with self.assertRaises(SolverException):
            Requirement._from_string(requirement_string)

    def test_from_legacy_requirement_string(self):
        # Given
        requirement_s = "numpy 1.8.1"

        # When
        requirement = Requirement.from_legacy_requirement_string(requirement_s)

        # Then
        self.assertEqual(requirement.name, "numpy")
        self.assertEqual(requirement._constraints,
                         MultiConstraints([EnpkgUpstreamMatch(V("1.8.1"))]))

        # Given
        requirement_s = "numpy 1.8.1-2"

        # When
        requirement = Requirement.from_legacy_requirement_string(requirement_s)

        # Then
        self.assertEqual(requirement.name, "numpy")
        self.assertEqual(requirement._constraints,
                         MultiConstraints([Equal(V("1.8.1-2"))]))

        # Given
        requirement_s = "numpy"

        # When
        requirement = Requirement.from_legacy_requirement_string(requirement_s)

        # Then
        self.assertEqual(requirement.name, "numpy")
        self.assertEqual(requirement._constraints,
                         MultiConstraints([Any()]))

        # Given
        requirement_s = " "

        # When/Then
        with self.assertRaises(ValueError):
            Requirement.from_legacy_requirement_string(requirement_s)

    def test_from_package_string(self):
        # Given
        package_s = "numpy-1.8.1-1"

        # When
        requirement = Requirement.from_package_string(package_s)

        # Then
        self.assertEqual(requirement.name, "numpy")
        self.assertEqual(requirement._constraints,
                         MultiConstraints([Equal(V("1.8.1-1"))]))


class TestParsePackageFullName(unittest.TestCase):
    def test_simple(self):
        # Given
        package_s = "numpy-1.8.1-1"

        # When
        name, version = parse_package_full_name(package_s)

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, "1.8.1-1")

        # Given
        package_s = "numpy 1.8.1"

        # When/Then
        with self.assertRaises(EnstallerException):
            parse_package_full_name(package_s)
