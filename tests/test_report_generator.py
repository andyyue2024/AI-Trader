# -*- coding: utf-8 -*-
"""
报告生成器单元测试
"""

import os
import pytest
import tempfile
from datetime import date, datetime
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.report_generator import (
    ReportConfig, ReportData,
    PDFReportGenerator, ExcelReportGenerator,
    ReportScheduler,
    generate_pdf_report, generate_excel_report
)


class TestReportData:
    """报告数据测试"""

    def test_default_data(self):
        """测试默认数据"""
        data = ReportData()

        assert data.report_date == date.today()
        assert data.initial_equity == 0.0
        assert data.total_trades == 0

    def test_data_with_values(self):
        """测试带值的数据"""
        data = ReportData(
            symbols=["TQQQ", "QQQ"],
            initial_equity=50000.0,
            final_equity=52500.0,
            total_return=0.05,
            sharpe_ratio=2.5,
            max_drawdown=0.08,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.6
        )

        assert data.symbols == ["TQQQ", "QQQ"]
        assert data.total_return == 0.05
        assert data.sharpe_ratio == 2.5

    def test_to_dict(self):
        """测试转换为字典"""
        data = ReportData(
            symbols=["TQQQ"],
            initial_equity=50000.0,
            final_equity=51000.0
        )

        d = data.to_dict()

        assert "report_date" in d
        assert "account" in d
        assert "performance" in d
        assert d["symbols"] == ["TQQQ"]


class TestReportConfig:
    """报告配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = ReportConfig()

        assert config.title == "AI-Trader Performance Report"
        assert config.include_charts == True
        assert config.include_trades == True

    def test_custom_config(self):
        """测试自定义配置"""
        config = ReportConfig(
            title="Custom Report",
            author="Test User",
            include_charts=False,
            output_dir="./custom_reports"
        )

        assert config.title == "Custom Report"
        assert config.author == "Test User"
        assert config.include_charts == False


class TestPDFReportGenerator:
    """PDF 报告生成器测试"""

    @pytest.fixture
    def generator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportConfig(output_dir=tmpdir)
            yield PDFReportGenerator(config)

    @pytest.fixture
    def sample_data(self):
        return ReportData(
            symbols=["TQQQ", "QQQ"],
            initial_equity=50000.0,
            final_equity=52500.0,
            total_return=0.05,
            sharpe_ratio=2.5,
            sortino_ratio=3.0,
            max_drawdown=0.08,
            volatility=0.15,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            win_rate=0.6,
            profit_factor=1.8,
            avg_win=150.0,
            avg_loss=-100.0,
            fill_rate=0.98,
            avg_slippage=0.001,
            total_volume=500000.0,
            avg_daily_volume=50000.0
        )

    def test_generate_creates_file(self, generator, sample_data):
        """测试生成文件"""
        filepath = generator.generate(sample_data)

        assert filepath is not None
        assert Path(filepath).exists()

    def test_output_path_has_correct_extension(self, generator):
        """测试输出路径扩展名"""
        path = generator._get_output_path("pdf")

        assert path.endswith(".pdf")

    def test_text_fallback(self, generator, sample_data):
        """测试文本降级"""
        # 模拟 reportlab 不可用
        filepath = generator._generate_text_fallback(sample_data)

        assert Path(filepath).exists()
        assert filepath.endswith(".txt")

        # 验证内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "AI-Trader" in content
            assert "Sharpe Ratio" in content


class TestExcelReportGenerator:
    """Excel 报告生成器测试"""

    @pytest.fixture
    def generator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportConfig(output_dir=tmpdir)
            yield ExcelReportGenerator(config)

    @pytest.fixture
    def sample_data(self):
        return ReportData(
            symbols=["TQQQ"],
            initial_equity=50000.0,
            final_equity=52000.0,
            total_return=0.04,
            sharpe_ratio=2.2,
            max_drawdown=0.10,
            total_trades=50,
            trades=[
                {"timestamp": "2025-01-01T10:00:00", "symbol": "TQQQ", "side": "long", "quantity": 10, "price": 75.0, "pnl": 50.0, "commission": 1.0}
            ],
            daily_stats=[
                {"date": "2025-01-01", "starting_equity": 50000, "ending_equity": 50500, "daily_return": 0.01, "trade_count": 5, "win_rate": 0.6}
            ]
        )

    def test_generate_creates_file(self, generator, sample_data):
        """测试生成文件"""
        filepath = generator.generate(sample_data)

        assert filepath is not None
        assert Path(filepath).exists()

    def test_csv_fallback(self, generator, sample_data):
        """测试 CSV 降级"""
        filepath = generator._generate_csv_fallback(sample_data)

        assert Path(filepath).exists()
        assert filepath.endswith(".csv")


class TestReportScheduler:
    """报告调度器测试"""

    @pytest.fixture
    def scheduler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportConfig(output_dir=tmpdir)
            generators = {
                "pdf": PDFReportGenerator(config),
                "excel": ExcelReportGenerator(config)
            }
            yield ReportScheduler(generators)

    def test_generate_pdf(self, scheduler):
        """测试生成 PDF"""
        data = ReportData(symbols=["TQQQ"], initial_equity=50000.0)

        filepath = scheduler.generate_report(data, "pdf")

        assert filepath is not None
        assert Path(filepath).exists()

    def test_generate_excel(self, scheduler):
        """测试生成 Excel"""
        data = ReportData(symbols=["TQQQ"], initial_equity=50000.0)

        filepath = scheduler.generate_report(data, "excel")

        assert filepath is not None

    def test_invalid_format(self, scheduler):
        """测试无效格式"""
        data = ReportData()

        with pytest.raises(ValueError):
            scheduler.generate_report(data, "invalid")


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_generate_pdf_report(self):
        """测试便捷 PDF 生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportConfig(output_dir=tmpdir)
            data = ReportData(symbols=["TQQQ"])

            filepath = generate_pdf_report(data, config)

            assert filepath is not None

    def test_generate_excel_report(self):
        """测试便捷 Excel 生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ReportConfig(output_dir=tmpdir)
            data = ReportData(symbols=["TQQQ"])

            filepath = generate_excel_report(data, config)

            assert filepath is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
