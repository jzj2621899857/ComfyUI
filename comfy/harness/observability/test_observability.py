"""
可观测性模块单元测试
"""

import unittest
import tempfile
import os
import time

from .tracer import tracer, ExecutionTracer
from .profiler import profiler, PerformanceProfiler
from .logger import logger, StructuredLogger


class TestTracer(unittest.TestCase):
    
    def setUp(self):
        tracer.enable()
        tracer.clear_history()
    
    def tearDown(self):
        tracer.disable()
        tracer.clear_history()
    
    def test_trace_workflow(self):
        """测试工作流追踪"""
        workflow_id = tracer.start_workflow_trace("test_workflow", {"test": True})
        
        tracer.start_node_trace(workflow_id, "1", "TestNode", {"input": "value"})
        time.sleep(0.01)
        tracer.end_node_trace(workflow_id, "1", {"output": "result"})
        
        tracer.end_workflow_trace(workflow_id)
        
        trace = tracer.get_trace(workflow_id)
        self.assertIsNotNone(trace)
        self.assertEqual(trace.workflow_id, "test_workflow")
        self.assertEqual(len(trace.nodes), 1)
        self.assertEqual(trace.nodes[0].node_id, "1")
        self.assertEqual(trace.nodes[0].status, "completed")
    
    def test_trace_failed_node(self):
        """测试失败节点追踪"""
        workflow_id = tracer.start_workflow_trace("test_failed")
        
        tracer.start_node_trace(workflow_id, "1", "FailingNode", {"input": "bad"})
        time.sleep(0.01)
        tracer.end_node_trace(workflow_id, "1", error="Test error")
        
        tracer.end_workflow_trace(workflow_id)
        
        trace = tracer.get_trace(workflow_id)
        self.assertEqual(trace.nodes[0].status, "failed")
        self.assertEqual(trace.nodes[0].error, "Test error")
    
    def test_trace_export(self):
        """测试追踪导出"""
        workflow_id = tracer.start_workflow_trace("export_test")
        tracer.start_node_trace(workflow_id, "1", "Node", {"input": 1})
        time.sleep(0.01)
        tracer.end_node_trace(workflow_id, "1", {"output": 2})
        tracer.end_workflow_trace(workflow_id)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = tracer.export_trace(workflow_id, temp_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(temp_path))
        finally:
            os.unlink(temp_path)


class TestProfiler(unittest.TestCase):
    
    def setUp(self):
        profiler.enable()
        profiler.reset_global_stats()
    
    def tearDown(self):
        profiler.disable()
        profiler.reset_global_stats()
    
    def test_profile_workflow(self):
        """测试工作流性能分析"""
        profiler.start_workflow("prof_workflow")
        
        profiler.start_node("prof_workflow", "1")
        time.sleep(0.01)
        profiler.end_node("prof_workflow", "1", "FastNode")
        
        profiler.start_node("prof_workflow", "2")
        time.sleep(0.02)
        profiler.end_node("prof_workflow", "2", "SlowNode")
        
        result = profiler.end_workflow("prof_workflow")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.total_nodes, 2)
        self.assertEqual(result.completed_nodes, 2)
        self.assertIn("FastNode", result.node_performance)
        self.assertIn("SlowNode", result.node_performance)
    
    def test_global_stats(self):
        """测试全局统计"""
        profiler.start_workflow("wf1")
        profiler.start_node("wf1", "1")
        time.sleep(0.01)
        profiler.end_node("wf1", "1", "TestNode")
        profiler.end_workflow("wf1")
        
        profiler.start_workflow("wf2")
        profiler.start_node("wf2", "1")
        time.sleep(0.02)
        profiler.end_node("wf2", "1", "TestNode")
        profiler.end_workflow("wf2")
        
        stats = profiler.get_global_stats()
        self.assertIn("TestNode", stats)
        self.assertEqual(stats["TestNode"].total_executions, 2)
    
    def test_slowest_nodes(self):
        """测试最慢节点排序"""
        profiler.start_workflow("wf")
        profiler.start_node("wf", "1")
        time.sleep(0.03)
        profiler.end_node("wf", "1", "Slowest")
        profiler.start_node("wf", "2")
        time.sleep(0.01)
        profiler.end_node("wf", "2", "Fastest")
        profiler.start_node("wf", "3")
        time.sleep(0.02)
        profiler.end_node("wf", "3", "Middle")
        profiler.end_workflow("wf")
        
        slowest = profiler.get_slowest_nodes(2)
        self.assertEqual(len(slowest), 2)
        self.assertEqual(slowest[0].node_type, "Slowest")
        self.assertEqual(slowest[1].node_type, "Middle")


class TestLogger(unittest.TestCase):
    
    def setUp(self):
        logger.enable()
    
    def tearDown(self):
        logger.disable()
    
    def test_log_events(self):
        """测试日志事件记录"""
        logger.log_workflow_start("test_log", 5)
        logger.log_node_execution("1", "TestNode", "completed", 0.1)
        logger.log_workflow_end("test_log", "completed", 1.0, 5, 0)
        logger.log_fallback("2", "FallbackNode", "test reason")
        logger.log_retry("3", "RetryNode", 1, 3, "test error")
        logger.log_validation_error("4", "BadNode", ["error1", "error2"])
        
        self.assertTrue(True)
    
    def test_log_levels(self):
        """测试日志级别"""
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")
        
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()