"""
Fuse Box 校验器单元测试
"""

import unittest
from unittest.mock import patch, MagicMock

from .fuse_box import FuseBoxValidator, ValidationResult, InputContract


class TestFuseBoxValidator(unittest.TestCase):
    
    def setUp(self):
        """初始化测试环境"""
        from ..config import FuseBoxConfig
        config = FuseBoxConfig(enabled=True, strict_mode=False)
        self.validator = FuseBoxValidator(config)
    
    def test_validate_type_valid(self):
        """测试有效类型校验"""
        valid_inputs = {
            "int": 42,
            "float": 3.14,
            "str": "test",
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
        }
        
        for name, value in valid_inputs.items():
            result = self.validator._validate_type(name, value)
            self.assertTrue(result.is_valid, f"类型 {type(value)} 应该有效")
    
    def test_validate_type_none(self):
        """测试 None 输入"""
        result = self.validator._validate_type("test", None)
        self.assertFalse(result.is_valid)
        self.assertIn("None", result.error_message)
    
    def test_validate_shape_matching(self):
        """测试 shape 匹配校验"""
        expected_shape = (1, 3, (512, 1024), (512, 1024))
        
        valid, msg = self.validator._validate_shape("test", (1, 3, 512, 512), expected_shape)
        self.assertTrue(valid)
    
    def test_validate_shape_mismatch(self):
        """测试 shape 不匹配校验"""
        expected_shape = (1, 3, 512, 512)
        
        valid, msg = self.validator._validate_shape("test", (1, 3, 256, 256), expected_shape)
        self.assertFalse(valid)
        self.assertIn("256", msg)
    
    def test_validate_inputs_all_valid(self):
        """测试所有输入都有效的情况"""
        inputs = {
            "prompt": "a beautiful landscape",
            "seed": 42,
            "strength": 0.5,
        }
        
        result = self.validator.validate_inputs("node_0", "TestNode", inputs)
        self.assertTrue(result.is_valid)
    
    def test_validate_inputs_with_invalid(self):
        """测试包含无效输入的情况"""
        inputs = {
            "image": None,
            "prompt": "a beautiful landscape",
        }
        
        result = self.validator.validate_inputs("node_0", "TestNode", inputs)
        self.assertFalse(result.is_valid)
    
    def test_input_contract(self):
        """测试输入合约"""
        contract = InputContract(
            name="image",
            dtype="float32",
            shape=(1, 3, (256, 1024), (256, 1024)),
            value_range=(0.0, 1.0),
            device="cuda",
            optional=False,
            description="输入图像 tensor"
        )
        
        self.assertEqual(contract.name, "image")
        self.assertEqual(contract.shape, (1, 3, (256, 1024), (256, 1024)))
        
        data = contract.to_dict()
        restored = InputContract.from_dict(data)
        self.assertEqual(restored.name, "image")
    
    def test_stats(self):
        """测试统计功能"""
        stats = self.validator.get_stats()
        self.assertEqual(stats["total_validations"], 0)
        
        self.validator.validate_inputs("node_0", "TestNode", {"input": 1})
        self.validator.validate_inputs("node_1", "TestNode", {"input": None})
        
        stats = self.validator.get_stats()
        self.assertEqual(stats["total_validations"], 2)
        self.assertEqual(stats["failed_validations"], 1)


if __name__ == "__main__":
    unittest.main()


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Running Fuse Box Validator Tests")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFuseBoxValidator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"测试结果: {result.testsRun} 个测试，"
          f"失败: {len(result.failures)}，错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()