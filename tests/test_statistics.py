"""
测试 StatisticsPanel 统计计算
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.statistics import StatisticsPanel


class TestStatisticsPanel:
    def setup_method(self):
        self.stats = StatisticsPanel()

    def test_initial_state_is_zero(self):
        assert self.stats.stats['pdf_parsed'] == 0
        assert self.stats.stats['notes_generated'] == 0
        assert self.stats.stats['total_time'] == 0

    def test_record_pdf_parsed_increments(self):
        self.stats.record_pdf_parsed(5)
        assert self.stats.stats['pdf_parsed'] == 5
        self.stats.record_pdf_parsed(3)
        assert self.stats.stats['pdf_parsed'] == 8

    def test_record_notes_generated_increments(self):
        self.stats.record_notes_generated(10)
        assert self.stats.stats['notes_generated'] == 10

    def test_stage_timing(self):
        self.stats.start_stage("parse")
        self.stats.end_stage("parse")
        assert "parse" in self.stats.stats['stage_times']
        assert self.stats.stats['stage_times']["parse"] >= 0

    def test_set_total_time(self):
        self.stats.set_total_time(42.5)
        assert self.stats.stats['total_time'] == 42.5

    def test_generate_report_includes_stages(self):
        self.stats.record_pdf_parsed(3)
        self.stats.record_notes_generated(3)
        self.stats.set_total_time(10.0)
        report = self.stats.generate_report()
        assert "PDF解析: 3" in report
        assert "笔记生成: 3" in report
        assert "总耗时: 10.0秒" in report
