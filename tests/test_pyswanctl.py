#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from click.testing import CliRunner

from pyswanctl.__main__ import cli


def test_main():
    runner = CliRunner()
    result = runner.invoke(cli, [])

    assert result.output == 'Pyswanctl main command line invoked.\n'
    assert result.exit_code == 0
