"""
Harness 模块统一测试运行器

运行所有 Harness 模块的单元测试，并生成测试报告
"""

import os
import sys
import unittest
from typing import List, Dict, Tuple


def run_all_tests() -> Tuple[bool, Dict[str, int]]:
    """
    运行所有测试
    
    Returns:
        tuple: (是否全部通过, 测试统计)
    """
    print("=" * 70)
    print("ComfyUI Harness 模块测试套件")
    print("=" * 70)
    
    # 收集所有测试模块
    test_modules = [
        ("Fuse Box", "comfy.harness.execution.test_fuse_box"),
        ("Fallback", "comfy.harness.execution.test_fallback"),
        ("Retry", "comfy.harness.execution.test_retry"),
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    all_passed = True
    
    for module_name, module_path in test_modules:
        print(f"\n{'=' * 70}")
        print(f"正在测试: {module_name}")
        print(f"{'=' * 70}")
        
        try:
            # 导入测试模块
            module = __import__(module_path, fromlist=["run_tests"])
            run_tests_func = getattr(module, "run_tests")
            
            # 运行测试
            passed = run_tests_func()
            
            # 更新统计
            suite = unittest.TestLoader().loadTestsFromModule(module)
            runner = unittest.TextTestRunner(verbosity=0)
            result = runner.run(suite)
            
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"❌ 测试模块加载失败: {e}")
            total_errors += 1
            all_passed = False
    
    # 输出汇总报告
    print("\n" + "=" * 70)
    print("测试汇总报告")
    print("=" * 70)
    print(f"总测试数: {total_tests}")
    print(f"通过: {total_tests - total_failures - total_errors}")
    print(f"失败: {total_failures}")
    print(f"错误: {total_errors}")
    print("=" * 70)
    
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    
    return all_passed, {
        "total": total_tests,
        "passed": total_tests - total_failures - total_errors,
        "failures": total_failures,
        "errors": total_errors
    }


def run_specific_test(module_name: str) -> bool:
    """
    运行特定测试模块
    
    Args:
        module_name: 模块名称 (FuseBox, Fallback, Retry)
    
    Returns:
        bool: 是否通过
    """
    modules = {
        "fusebox": "comfy.harness.execution.test_fuse_box",
        "fallback": "comfy.harness.execution.test_fallback",
        "retry": "comfy.harness.execution.test_retry",
    }
    
    module_path = modules.get(module_name.lower())
    if not module_path:
        print(f"❌ 未知模块: {module_name}")
        return False
    
    try:
        module = __import__(module_path, fromlist=["run_tests"])
        return getattr(module, "run_tests")()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 检查参数
    if len(sys.argv) > 1:
        # 运行特定测试
        module_name = sys.argv[1]
        success = run_specific_test(module_name)
        sys.exit(0 if success else 1)
    else:
        # 运行所有测试
        success, stats = run_all_tests()
        sys.exit(0 if success else 1)