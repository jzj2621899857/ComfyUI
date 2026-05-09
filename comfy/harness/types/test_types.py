"""
类型系统单元测试
"""

import unittest
import tempfile
import os

from .contracts import PortContract, NodeContract, validate_connection
from .registry import TypeRegistry, register_standard_contracts, registry
from .compiler import GraphCompiler, compile_workflow


class TestPortContract(unittest.TestCase):
    
    def test_port_contract_validate_valid(self):
        """测试端口合约验证（有效输入）"""
        contract = PortContract(
            name="value",
            dtype="int",
            value_range=(0, 100),
        )
        
        # 有效输入
        valid, msg = contract.validate(50)
        self.assertTrue(valid)
        self.assertEqual(msg, "")
    
    def test_port_contract_validate_invalid_value(self):
        """测试端口合约验证（无效值范围）"""
        contract = PortContract(
            name="value",
            dtype="int",
            value_range=(0, 100),
        )
        
        # 无效值 - 超出范围
        invalid_value = 200
        
        valid, msg = contract.validate(invalid_value)
        self.assertFalse(valid)
        self.assertIn("数值超出范围", msg)
    
    def test_port_contract_optional(self):
        """测试可选端口"""
        optional_contract = PortContract(name="optional_input", optional=True)
        required_contract = PortContract(name="required_input", optional=False)
        
        # 可选端口允许 None
        valid, _ = optional_contract.validate(None)
        self.assertTrue(valid)
        
        # 必填端口不允许 None
        valid, _ = required_contract.validate(None)
        self.assertFalse(valid)
    
    def test_port_contract_serialization(self):
        """测试端口合约序列化"""
        contract = PortContract(
            name="test",
            dtype="float32",
            shape=(1, 3, -1, -1),
            value_range=(0.0, 1.0),
            color_space="RGB"
        )
        
        # 序列化
        data = contract.to_dict()
        
        # 反序列化
        restored = PortContract.from_dict(data)
        
        self.assertEqual(restored.name, contract.name)
        self.assertEqual(restored.dtype, contract.dtype)
        self.assertEqual(restored.shape, contract.shape)


class TestNodeContract(unittest.TestCase):
    
    def test_node_contract_validate_inputs(self):
        """测试节点合约验证输入"""
        contract = NodeContract(
            node_type="TestNode",
            inputs=[
                PortContract(name="width", dtype="int", value_range=(0, 1024)),
                PortContract(name="height", dtype="int", value_range=(0, 1024)),
                PortContract(name="strength", dtype="float", value_range=(0.0, 1.0)),
            ],
            outputs=[
                PortContract(name="output", dtype="float32"),
            ]
        )
        
        # 有效输入
        inputs = {
            "width": 512,
            "height": 512,
            "strength": 0.5,
        }
        
        valid, errors = contract.validate_inputs(inputs)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
    
    def test_node_contract_validate_invalid_inputs(self):
        """测试节点合约验证无效输入"""
        contract = NodeContract(
            node_type="TestNode",
            inputs=[
                PortContract(name="value", dtype="int", value_range=(0, 100)),
            ],
            outputs=[]
        )
        
        # 无效输入
        inputs = {"value": 200}
        
        valid, errors = contract.validate_inputs(inputs)
        self.assertFalse(valid)
        self.assertEqual(len(errors), 1)
    
    def test_node_contract_save_load(self):
        """测试节点合约保存和加载"""
        contract = NodeContract(
            node_type="TestNode",
            inputs=[PortContract(name="input")],
            outputs=[PortContract(name="output")],
            version="1.0.0"
        )
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            contract.save(temp_path)
            
            # 加载
            loaded = NodeContract.load(temp_path)
            
            self.assertEqual(loaded.node_type, contract.node_type)
            self.assertEqual(len(loaded.inputs), len(contract.inputs))
        finally:
            os.unlink(temp_path)


class TestConnectionValidation(unittest.TestCase):
    
    def test_validate_connection_valid(self):
        """测试连接验证（有效连接）"""
        source = PortContract(name="out", dtype="float32", shape=(1, 3, -1, -1))
        target = PortContract(name="inp", dtype="float32", shape=(1, 3, -1, -1))
        
        result = validate_connection(source, target)
        self.assertTrue(result.is_valid)
    
    def test_validate_connection_type_mismatch(self):
        """测试连接验证（类型不匹配）"""
        source = PortContract(name="out", dtype="float16")
        target = PortContract(name="inp", dtype="float32")
        
        result = validate_connection(source, target)
        # float16 -> float32 是允许的向上转换
        self.assertTrue(result.is_valid)
    
    def test_validate_connection_dimension_mismatch(self):
        """测试连接验证（维度不匹配）"""
        source = PortContract(name="out", dtype="float32", shape=(1, 3, -1, -1))
        target = PortContract(name="inp", dtype="float32", shape=(1, 4, -1, -1))
        
        result = validate_connection(source, target)
        self.assertFalse(result.is_valid)


class TestTypeRegistry(unittest.TestCase):
    
    def setUp(self):
        """重置注册表状态"""
        registry.clear()
    
    def tearDown(self):
        """清理注册表"""
        registry.clear()
    
    def test_register_contract(self):
        """测试注册合约"""
        contract = NodeContract(
            node_type="TestNode",
            inputs=[PortContract(name="input")],
            outputs=[PortContract(name="output")]
        )
        
        registry.register_contract(contract)
        
        self.assertTrue(registry.has_contract("TestNode"))
        self.assertEqual(registry.get_contract("TestNode").node_type, "TestNode")
    
    def test_register_standard_contracts(self):
        """测试注册标准合约"""
        register_standard_contracts()
        
        stats = registry.get_stats()
        self.assertGreater(stats["total_contracts"], 0)
        
        # 检查几个标准合约
        self.assertTrue(registry.has_contract("KSampler"))
        self.assertTrue(registry.has_contract("VAEEncode"))
        self.assertTrue(registry.has_contract("VAEDecode"))
    
    def test_register_alias(self):
        """测试注册别名"""
        contract = NodeContract(node_type="OriginalNode", inputs=[], outputs=[])
        registry.register_contract(contract)
        registry.register_alias("AliasNode", "OriginalNode")
        
        # 通过别名获取合约
        result = registry.get_contract("AliasNode")
        self.assertIsNotNone(result)
        self.assertEqual(result.node_type, "OriginalNode")


class TestGraphCompiler(unittest.TestCase):
    
    def setUp(self):
        """重置注册表状态"""
        registry.clear()
        register_standard_contracts()
    
    def tearDown(self):
        """清理注册表"""
        registry.clear()
    
    def test_compile_valid_workflow(self):
        """测试编译有效工作流"""
        workflow = {
            "nodes": {
                "1": {"type": "CLIPTextEncode", "inputs": {"text": "test", "clip": "clip_model"}},
                "2": {"type": "CLIPTextEncode", "inputs": {"text": "negative", "clip": "clip_model"}},
            },
            "connections": []
        }
        
        compiler = GraphCompiler()
        success, errors, warnings = compiler.compile(workflow)
        
        self.assertTrue(success)
        self.assertEqual(len(errors), 0)
    
    def test_compile_missing_input(self):
        """测试编译缺少输入的工作流"""
        workflow = {
            "nodes": {
                "1": {"type": "CLIPTextEncode"},  # 缺少 text 输入
            },
            "connections": []
        }
        
        compiler = GraphCompiler(strict_mode=True)
        success, errors, warnings = compiler.compile(workflow)
        
        # 应该有错误（缺少必填输入）
        self.assertFalse(success)
    
    def test_compile_workflow_function(self):
        """测试 compile_workflow 便捷函数"""
        workflow = {
            "nodes": {
                "1": {"type": "CLIPTextEncode", "inputs": {"text": "hello", "clip": "clip_model"}},
            },
            "connections": []
        }
        
        result = compile_workflow(workflow)
        
        self.assertTrue(result["success"])
        self.assertEqual(len(result["errors"]), 0)


if __name__ == "__main__":
    unittest.main()


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Running Type System Tests")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPortContract)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestNodeContract))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionValidation))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTypeRegistry))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphCompiler))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"测试结果: {result.testsRun} 个测试，"
          f"失败: {len(result.failures)}，错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()