#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行所有测试
"""

import subprocess
import sys
import os


def run_tests():
    """运行测试套件"""
    print("=" * 60)
    print("  AI-Trader Test Suite")
    print("=" * 60)

    # 切换到项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # 运行单元测试
    print("\n📋 Running Unit Tests...")
    print("-" * 40)

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=futu",
            "--cov=risk_control",
            "--cov=monitoring",
            "--cov=backtest",
            "--cov=web",
            "--cov=reports",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_report",
            "-x"  # 遇到第一个失败就停止
        ],
        cwd=project_root
    )

    if result.returncode != 0:
        print("\n❌ Tests failed!")
        return result.returncode

    print("\n✅ All tests passed!")
    print(f"\n📊 Coverage report: {project_root}/coverage_report/index.html")

    return 0


def run_quick_tests():
    """运行快速测试（不包括集成测试）"""
    print("\n📋 Running Quick Tests (excluding integration)...")

    project_root = os.path.dirname(os.path.abspath(__file__))

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-m", "not integration",
            "-x"
        ],
        cwd=project_root
    )

    return result.returncode


def run_coverage():
    """运行覆盖率测试"""
    print("\n📊 Running Coverage Analysis...")

    project_root = os.path.dirname(os.path.abspath(__file__))

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=futu",
            "--cov=risk_control",
            "--cov=monitoring",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_report",
            "--cov-fail-under=80"  # 覆盖率必须达到80%
        ],
        cwd=project_root
    )

    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AI-Trader tests")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (exclude integration)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage analysis"
    )

    args = parser.parse_args()

    if args.quick:
        exit_code = run_quick_tests()
    elif args.coverage:
        exit_code = run_coverage()
    else:
        exit_code = run_tests()

    sys.exit(exit_code)
