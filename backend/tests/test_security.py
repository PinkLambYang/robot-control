"""
安全功能测试 - JWT 认证和消息加密

Python 3.8+ 兼容
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import time
from utils.auth import TokenExtractor
from utils.crypto_js_compat import CryptoJSAES

# 可选依赖
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class TestTokenExtractor(unittest.TestCase):
    """Token 提取器测试"""
    
    def test_token_extractor_query_string(self):
        """测试从查询字符串提取 Token"""
        token = TokenExtractor.extract_from_query_string('token=abc123&foo=bar')
        self.assertEqual(token, 'abc123')
        
        token = TokenExtractor.extract_from_query_string('auth=xyz789')
        self.assertEqual(token, 'xyz789')
        
        token = TokenExtractor.extract_from_query_string('foo=bar')
        self.assertIsNone(token)
    
    def test_token_extractor_headers(self):
        """测试从 Headers 提取 Token"""
        headers = {'Authorization': 'Bearer abc123'}
        token = TokenExtractor.extract_from_headers(headers)
        self.assertEqual(token, 'abc123')
        
        headers = {'authorization': 'Bearer xyz789'}
        token = TokenExtractor.extract_from_headers(headers)
        self.assertEqual(token, 'xyz789')
        
        headers = {'Authorization': 'InvalidFormat'}
        token = TokenExtractor.extract_from_headers(headers)
        self.assertIsNone(token)
    
    def test_token_extractor_environ(self):
        """测试从 environ 提取 Token"""
        # 从查询字符串
        environ = {'QUERY_STRING': 'token=abc123&foo=bar'}
        token = TokenExtractor.extract_from_environ(environ)
        self.assertEqual(token, 'abc123')
        
        # 从 HTTP 头
        environ = {
            'QUERY_STRING': '',
            'HTTP_AUTHORIZATION': 'Bearer xyz789'
        }
        token = TokenExtractor.extract_from_environ(environ)
        self.assertEqual(token, 'xyz789')
        
        # 没有 token
        environ = {'QUERY_STRING': 'foo=bar'}
        token = TokenExtractor.extract_from_environ(environ)
        self.assertIsNone(token)


class TestCryptoJSCompat(unittest.TestCase):
    """crypto-js 兼容加密测试"""
    
    def setUp(self):
        self.crypto = CryptoJSAES('ROBOT_CONTROL_SYSTEM')
    
    def test_encrypt_decrypt(self):
        """测试加密和解密"""
        data = {'command': 'test', 'value': 123}
        
        # 加密
        success, encrypted, error = self.crypto.encrypt(data)
        self.assertTrue(success, f"加密失败: {error}")
        self.assertIsNotNone(encrypted)
        self.assertIsInstance(encrypted, str)
        self.assertTrue(encrypted.startswith('U2FsdGVkX1'), "应该以 'U2FsdGVkX1' 开头")
        
        # 解密
        success, decrypted, error = self.crypto.decrypt(encrypted)
        self.assertTrue(success, f"解密失败: {error}")
        self.assertEqual(decrypted, data)
    
    def test_decrypt_invalid_data(self):
        """测试解密无效数据"""
        success, decrypted, error = self.crypto.decrypt('invalid_encrypted_data')
        self.assertFalse(success)
        self.assertIsNone(decrypted)
        self.assertNotEqual(error, '')
    
    def test_encrypt_complex_data(self):
        """测试加密复杂数据（包含中文）"""
        data = {
            'status': 'success',
            'message': '操作成功',
            'params': {
                'object': 'robot',
                'method': 'move',
                'args': {'x': 100, 'y': 200},
                'nested': {
                    'list': [1, 2, 3],
                    'dict': {'name': '测试'}
                }
            }
        }
        
        success, encrypted, error = self.crypto.encrypt(data)
        self.assertTrue(success, f"加密失败: {error}")
        
        success, decrypted, error = self.crypto.decrypt(encrypted)
        self.assertTrue(success, f"解密失败: {error}")
        self.assertEqual(decrypted, data)
    
    def test_different_keys(self):
        """测试不同密钥无法解密"""
        crypto1 = CryptoJSAES('key1')
        crypto2 = CryptoJSAES('key2')
        
        data = {'test': 'data'}
        
        success, encrypted, _ = crypto1.encrypt(data)
        self.assertTrue(success)
        
        # 使用不同密钥解密应该失败
        success, decrypted, error = crypto2.decrypt(encrypted)
        self.assertFalse(success)
        self.assertIsNone(decrypted)




class TestHTTPEndpoints(unittest.TestCase):
    """HTTP 端点集成测试（需要服务器运行和 requests 库）"""
    
    @classmethod
    def setUpClass(cls):
        cls.server_url = 'http://localhost:8000'
        cls.skip_integration = False
        
        if not HAS_REQUESTS:
            cls.skip_integration = True
            print("\n⚠️  跳过集成测试：未安装 requests 库")
            return
        
        # 检查服务器是否运行
        try:
            requests.get(cls.server_url, timeout=1)
        except:
            cls.skip_integration = True
            print("\n⚠️  跳过集成测试：服务器未运行")
    
    def setUp(self):
        if self.skip_integration:
            self.skipTest("服务器未运行或缺少依赖")
    
    def test_root_endpoint(self):
        """测试根端点返回服务信息"""
        response = requests.get(self.server_url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['service'], 'Robot Control System')
        self.assertEqual(data['protocol'], 'Socket.IO')
        self.assertIn('security', data)
        self.assertIn('auth_service', data)
        
        # 验证不提供 token 生成功能
        security = data['security']
        self.assertTrue(security['jwt_enabled'])
        self.assertEqual(security['auth_mode'], 'public_key')


def run_tests():
    """运行测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestTokenExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptoJSCompat))
    suite.addTests(loader.loadTestsFromTestCase(TestHTTPEndpoints))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

