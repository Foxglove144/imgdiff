import doctest
import os
import shutil
import sys
import tempfile
import unittest

import mock

import imgdiff

from io import StringIO


@mock.patch("sys.stderr", StringIO())
class TestMain(unittest.TestCase):

    def setUp(self):
        self.tmpdir = None
        # Patch spawn_viewer to prevent subprocess calls during tests
        self.patcher = mock.patch("imgdiff.spawn_viewer")
        self.mock_spawn_viewer = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if self.tmpdir:
            shutil.rmtree(self.tmpdir)

    def mkdtemp(self):
        if self.tmpdir is None:
            self.tmpdir = tempfile.mkdtemp(prefix="imgdiff-tests-")
        return self.tmpdir

    def main(self, *args):
        try:
            imgdiff.main(["imgdiff"] + list(args))
        except SystemExit:
            pass

    def test_color_parsing_in_options(self):
        self.main("--bgcolor", "invalid", "foo", "bar")
        self.assertIn(
            "error: option --bgcolor: invalid color value: 'invalid'",
            sys.stderr.getvalue(),
        )

    def test_wrong_number_of_arguments(self):
        self.main("foo.png")
        self.assertIn("error: expecting two arguments, got 1", sys.stderr.getvalue())
        self.main("foo.png", "bar.png", "baz.png")
        self.assertIn("error: expecting two arguments, got 3", sys.stderr.getvalue())

    def test_two_directories(self):
        self.main("set1", "set2")
        self.assertIn(
            "error: at least one argument must be a file, not a directory",
            sys.stderr.getvalue(),
        )

    def test_all_ok(self):
        self.main("example1.png", "example2.png", "--viewer=true")

    def test_highlight(self):
        self.main("example1.png", "example2.png", "-H", "--viewer=true")

    def test_smart_highlight(self):
        self.main("example1.png", "example2.png", "-S", "--viewer=true")

    def test_outfile(self):
        fn = os.path.join(self.mkdtemp(), "diff.png")
        self.main("example1.png", "example2.png", "-o", fn)
        self.assertTrue(os.path.exists(fn))

    @mock.patch("imgdiff.Image.Image.show")
    def test_builtin_viewer(self, mock_show):
        self.main("example1.png", "example2.png")
        self.assertTrue(mock_show.called)

    def test_one_directory(self):
        self.main("set1/canary.png", "set2", "--viewer", "true")
        self.main("set1", "set2/canary.png", "--viewer", "true", "--tb")

    def test_different_size_images(self):
        # tickle the unexplored branches in best_diff()
        self.main("set1/extra-info.png", "set1/sample-graph.png", "--viewer=true", "-H")

    def test_different_size_images_sloow(self):
        # tickle the unexplored branches in slow_highlight()
        self.main("set1/extra-info.png", "set1/sample-graph.png", "--viewer=true", "-S")


class TestProgress(unittest.TestCase):

    def test_terminal_output(self):
        p = imgdiff.Progress(3, delay=0)
        p.stream = StringIO()
        p.isatty = True
        for n in range(3):
            p.next()
        p.done()
        self.assertEqual(
            p.stream.getvalue(),
            "\r33% (1 out of 3 possible alignments)"
            "\r66% (2 out of 3 possible alignments)"
            "\r100% (3 out of 3 possible alignments)"
            "\r\n",
        )

    def test_not_a_terminal(self):
        p = imgdiff.Progress(3, delay=0)
        p.stream = StringIO()
        p.isatty = False
        for n in range(3):
            p.next()
        p.done()
        self.assertEqual(p.stream.getvalue(), "")

    def test_cancel(self):
        cancel_event = mock.Mock()
        cancel_event.is_set.return_value = False

        p = imgdiff.Progress(3, cancel_event=cancel_event)
        p.stream = StringIO()
        p.isatty = False

        # should run fine if not cancelled
        p.next()

        # now cancel
        cancel_event.is_set.return_value = True
        self.assertRaises(imgdiff.Timeout, p.next)

        # done() shouldn't do anything since nothing was printed to the stream
        p.done()
        self.assertEqual(p.stream.getvalue(), "")


def test_suite():
    return unittest.TestSuite(
        [
            doctest.DocTestSuite(imgdiff),
            unittest.defaultTestLoader.loadTestsFromName(__name__),
        ]
    )


if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
