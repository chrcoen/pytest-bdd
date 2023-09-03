from __future__ import annotations

import typing

from _pytest.terminal import TerminalReporter
from _pytest._code.code import TerminalRepr

if typing.TYPE_CHECKING:
    from typing import Any

    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.reports import TestReport


def add_options(parser: Parser) -> None:
    group = parser.getgroup("terminal reporting", "reporting", after="general")
    group._addoption(
        "--advanced-reporter",
        action="store_true",
        dest="advanced_reporter",
        default=False,
        help="enable advanced output",
    )


def configure(config: Config) -> None:
    if config.option.advanced_reporter:
        # Get the standard terminal reporter plugin and replace it with our
        current_reporter = config.pluginmanager.getplugin("terminalreporter")
        if current_reporter.__class__ != TerminalReporter:
            raise Exception(
                "advanced-terminal-reporter is not compatible with any other terminal reporter."
                "You can use only one terminal reporter."
                "Currently '{0}' is used."
                "Please decide to use one by deactivating {0} or advanced-reporter.".format(
                    current_reporter.__class__
                )
            )
        advanced_reporter = AdvancedReporter(config)
        config.pluginmanager.unregister(current_reporter)
        config.pluginmanager.register(advanced_reporter, "advancedreporter")
        if config.pluginmanager.getplugin("dsession"):
            raise Exception("advanced-reporter is not compatible with 'xdist' plugin.")


class AdvancedReporter(TerminalReporter):
    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def pytest_runtest_logreport(self, report: TestReport) -> Any:
        result = self.config.hook.pytest_report_teststatus(report=report, config=self.config)[0]
        if not result:
            return None
        if self.verbosity <= 0 or not hasattr(report, "scenario"):
            return super().pytest_runtest_logreport(report)
        
        self._tw.write(f': {report.scenario["name"]} ')
        if result == 'passed':
            self._tw.write("PASSED", green=True)
        elif result == 'failed':
            self._tw.write("FAILED", red=True)
            self.ensure_newline()
            self._tw.write("\nFeature: ")
            self._tw.write(report.scenario["feature"]["name"])
            self._tw.write("\n")
            self._tw.write("    Scenario: ")
            self._tw.write(report.scenario["name"])
            self._tw.write("\n")
            color = {"green": True}
            failed = False
            result_str = '  '
            for step in report.scenario["steps"]:
                if step['failed'] and not failed:
                    color = {"red": True}
                    failed = True
                    result_str = '->'
                self._tw.write(f"     {result_str} {step['keyword']:>5} {step['name']}\n", **color)
                if step['failed']:
                    failed = True
                    result_str = '  '
                    color = {"light": True}
            # Remove call_fixture_func from chain since it will only bloat output but give no information
            reporter = typing.cast(TerminalRepr, report.longrepr) 
            ignore = [element[0].reprentries.pop(0) if 'def call_fixture_func' in element[0].reprentries[0].lines[0] else None for element in reporter.chain]
            reporter.toterminal(self._tw)
            for element, ign in zip(reporter.chain, ignore):
                if ign is not None:
                    element[0].reprentries.insert(0, ignore)

        else:
            assert 0
        # self.stats.setdefault(result, []).append(report)
        return None
