# Lists the tests
#
# Copyright (C) 2015 Andrew Cagney <cagney@gnu.org>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See <http://www.fsf.org/copyleft/gpl.txt>.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

import os
import re
import collections
from fab import logutil
from fab import utils

class Test:

    def __init__(self, test_directory, kind, expected_result,
                 saved_test_output_directory=None,
                 testsuite_output_directory=None):
        self.logger = logutil.getLogger(__name__)
        # basics
        self.kind = kind
        self.expected_result = expected_result
        # The test's name is always identical to the test directory's
        # name (aka basename).  However, since TEST_DIRECTORY could be
        # relative (for instance "."  or "./..") it first needs to be
        # made absolute before the basename can be extracted.
        test_directory = os.path.abspath(test_directory)
        # The test's name is the same as the directory's basename.
        self.name = os.path.basename(test_directory)
        self.full_name = "test " + self.name
        # Construct the test's relative directory path such that it
        # always contains the test directory name (i.e., the test
        # name) as context.  For instance: "."  gets rewritten as
        # ../<test>; and ".." gets rewritten as "../../<test>".  This
        # ensures that displayed paths always include some context.
        # For instance, given "kvmresult.py .", "../<test> passed"
        # (and not ". passed") will be displayed.
        self.directory = os.path.join(os.path.relpath(os.path.dirname(test_directory)), self.name)
        # Directory where the next test run's output should be
        # written.  If a common testsuite output directory was
        # specified, use that.
        self.output_directory = (
            testsuite_output_directory
            and os.path.join(testsuite_output_directory, self.name)
            or os.path.join(self.directory, "OUTPUT"))
        self.result_file = os.path.join(self.output_directory, "RESULT")
        # Directory containing saved output from a previous test run.
        # If the test's output directory was explicitly specified, say
        # as a parameter to kvmrunner.py vis:
        #
        #   kvmresults.py testing/pluto/<test>/OUTPUT.OLD
        #   kvmresults.py testing/pluto/OUTPUT/<test>
        #
        # than that directory, and not the next output-directory, will
        # be passed in and saved here.  Otherwise it is None, and the
        # OUTPUT_DIRECTORY should be used.
        self.saved_output_directory = saved_test_output_directory
        # will be filled in later
        self.domains = None
        self.initiators = None

    def __str__(self):
        return self.full_name

    def files_with_suffix(self, suffix):
        s = set()
        for file in os.listdir(self.directory):
            host, init, t = file.partition(suffix)
            if init and not t:
                s.add(host)
        return s

    def domain_names(self):
        if not self.domains:
            self.domains = self.files_with_suffix("init.sh")
        return self.domains

    def initiator_names(self):
        if not self.initiators:
            self.initiators = self.files_with_suffix("run.sh")
        return self.initiators


class Testsuite:

    def __init__(self, logger, testlist, error_level,
                 testsuite_output_directory=None,
                 saved_testsuite_output_directory=None):
        self.directory = os.path.dirname(testlist)
        self.testlist = collections.OrderedDict()
        with open(testlist, 'r') as testlist_file:
            for line in testlist_file:
                line = line.strip()
                # these three log lines are ment to align
                if not line:
                    logger.debug("%7s: ", "blank")
                    continue
                if line[0] == '#':
                    logger.debug("%7s: %s", "comment", line)
                    continue
                logger.debug("%7s: %s", "input", line)
                try:
                    kind, name, expected_result = line.split()
                except ValueError:
                    # This is serious
                    logger.log(error_level,
                                    "****** malformed line: %s", line)
                    continue
                test = Test(kind=kind, expected_result=expected_result,
                            test_directory=os.path.join(self.directory, name),
                            saved_test_output_directory=(
                                saved_testsuite_output_directory
                                and os.path.join(saved_testsuite_output_directory, name)),
                            testsuite_output_directory=testsuite_output_directory)
                logger.debug("test directory: %s", test.directory)
                if not os.path.exists(test.directory):
                    # This is serious
                    logger.log(error_level,
                                    "****** invalid test %s: directory not found: %s",
                                    test.name, test.directory)
                    continue
                # an OrderedDict which saves insertion order
                self.testlist[test.name] = test

    def __iter__(self):
        return self.testlist.values().__iter__()

    def __contains__(self, index):
        return index in self.testlist

    def __getitem__(self, index):
        return self.testlist[index]

    def __len__(self):
        return self.testlist.__len__()

def add_arguments(parser):

    group = parser.add_argument_group("Test arguments",
                                      "Options for selecting the tests to run")
    group.add_argument("--test-name", default="",
                       type=re.compile, metavar="REGULAR-EXPRESSION",
                       help=("Select tests with name matching %(metavar)s"
                             " (default: '%(default)s')"))
    group.add_argument("--test-kind", default="kvmplutotest",
                       type=re.compile, metavar="REGULAR-EXPRESSION",
                       help=("Select tests with kind matching %(metavar)s"
                             " (default: '%(default)s')"))
    group.add_argument("--test-result", default="good",
                       type=re.compile, metavar="REGULAR-EXPRESSION",
                       help="Select tests with (expected) result matching %(metavar)s (default: '%(default)s')")
    group.add_argument("--test-exclude", default="",
                       type=re.compile, metavar="REGULAR-EXPRESSION",
                       help=("Exclude tests that match %(metavar)s"
                             " (default: '%(default)s')"))


def log_arguments(logger, args):
    logger.info("Testsuite arguments:")
    logger.info("  test-kind: '%s'" , args.test_kind.pattern)
    logger.info("  test-name: '%s'" , args.test_name.pattern)
    logger.info("  test-result: '%s'" , args.test_result.pattern)
    logger.info("  test-exclude: '%s'" , args.test_exclude.pattern)


TESTLIST = "TESTLIST"


def load(logger, directory, testsuite_output_directory=None, error_level=logutil.ERROR):
    """Load the testsuite (TESTLIST) found in DIRECTORY"""

    # Is DIRECTORY a testsuite?  For instance: testing/pluto.
    testlist = os.path.join(directory, TESTLIST)
    if os.path.exists(testlist):
        logger.debug("'%s' is a testsuite directory", directory)
        return Testsuite(logger, testlist, error_level,
                         testsuite_output_directory=testsuite_output_directory)

    # Is DIRECTORY a testsuite sub-directory containing testsuite
    # results?  For instance: testing/pluto/OUTPUT.  Exclude the
    # possibility that the sub-directory is a single test (i.e.,
    # "testing/pluto/<test>") by checking that the file
    # description.txt is absent.
    testlist = os.path.join(directory, "..", TESTLIST)
    if os.path.exists(testlist) \
    and not os.path.exists(os.path.join(directory, "description.txt")):
        logger.debug("'%s' is an output sub-directory under a testsuite", directory)
        return Testsuite(logger, testlist, error_level,
                         testsuite_output_directory=testsuite_output_directory,
                         saved_testsuite_output_directory=directory)

    logger.debug("'%s' does not appear to be a testsuite directory", directory)
    return None


def load_testsuite_or_tests(logger, directories, testsuite_output_directory=None, log_level=logutil.DEBUG):

    # If there is only one directory then, perhaps, it contains a full
    # testsuite.  The easiest way to find out is to try opening it.
    if len(directories) == 1:
        testsuite_directory = directories[0]
        testsuite = load(logger, testsuite_directory, testsuite_output_directory=testsuite_output_directory)
        if testsuite:
            logger.log(log_level, "testsuite: %s", testsuite_directory)
            return testsuite

    # There are multiple directories so, presumably, each one
    # specifies a single test that need to be "loaded".  Form a list
    # of the tests.
    tests = []
    for directory in directories:
        # Python's basename is close to useless - given "foo/" it
        # returns "" and not "foo" - get around this.
        if not os.path.basename(directory):
            directory = os.path.dirname(directory)
        test_directory = None
        saved_test_output_directory = None
        # Use heuristics to differentiate between a directory that
        # contains a test, and an old-output directory that contains
        # test output (hopefully, for the latter, there is a test
        # directory close by).
        if os.path.exists(os.path.join(directory, "description.txt")):
            # easy case, directory is a test
            logger.debug("'%s' matches <test> - a test directory", directory)
            test_directory = directory
        elif os.path.exists(os.path.join(directory, "..", "description.txt")):
            # DIRECTORY is a sub-directory of a test so, presumably,
            # it contains old test output.  Note that the test for the
            # path DIRECTORY/.. only works when DIRECTORY exists.  See
            # also next test.
            logger.debug("'%s' matches <test>/OUTPUT - a test output sub-directory", directory)
            saved_test_output_directory = directory
            test_directory = os.path.join(directory, "..")
        elif os.path.basename(directory).startswith("OUTPUT") \
        and os.path.exists(os.path.join(os.path.dirname(directory), "description.txt")):
            # DIRECTORY doesn't exist, yet it really really looks like
            # a test output sub-directory (if DIRECTORY did exist the
            # earlier test would have succeeded).  The sequence:
            #
            #   cd testing/pluto/<TEST>
            #   rm -rf OUTPUT
            #   kvmrunner.py !$
            #
            # will cause this.
            logger.debug("'%s' matches <test>/OUTPUT.* - a deleted test output sub-directory", directory)
            saved_test_output_directory = directory
            test_directory = os.path.dirname(directory)
        elif os.path.exists(os.path.join(directory, "..", "..", TESTLIST)) \
        and os.path.exists(os.path.join(directory, "..", "..", os.path.basename(directory), "description.txt")):
            # DIRECTORY is old saved test output under a testsuite
            # sub-directory.  The sequence:
            #
            #   mkdir testing/pluto/OUTPUT.YYMMDD
            #   mv testing/pluto/<TEST>/OUTPUT testing/pluto/OUTPUT.YYMMDD/<TEST>
            #   kvmrunner.py !$
            #
            # will cause this.  In the future this may be kvmrunner's
            # default behaviour.
            logger.debug("'%s' matches OUTPUT/<test>  - a test output directory saved in a testsuite directory", directory)
            saved_test_output_directory = directory
            test_directory = os.path.join(directory, "..", "..", os.path.basename(directory))
        else:
            logger.error("directory '%s' is invalid", directory)
            return None
        tests.append(Test(kind="kvmplutotest", expected_result="good",
                          test_directory=test_directory,
                          saved_test_output_directory=saved_test_output_directory,
                          testsuite_output_directory=testsuite_output_directory))

    return tests


def ignore(test, args):

    """Identify tests that should be ignored due to filters

    The ignore reason is returned.

    This is different to SKIP where a test isn't run because it has
    been run before.

    """

    if args.test_kind.pattern and not args.test_kind.search(test.kind):
        return "kind '%s' does not match '%s'" % (test.kind, args.test_kind.pattern)
    if args.test_name.pattern and not args.test_name.search(test.name):
        return "name '%s' does not match '%s'" % (test.name, args.test_name.pattern)
    if args.test_result.pattern and not args.test_result.search(test.expected_result):
        return "expected test result '%s' does not match '%s'" % (test.expected_result, args.test_result.pattern)

    if args.test_exclude.pattern:
        if args.test_exclude.search(test.kind) or \
           args.test_exclude.search(test.name) or \
           args.test_exclude.search(test.expected_result):
            return "matches exclude regular expression: %s" % args.test_exclude.pattern

    return None
