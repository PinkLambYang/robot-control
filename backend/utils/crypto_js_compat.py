"""与 crypto-js 兼容的加密/解密实现"""
import json
import base64
import logging
from typing import Dict, Any, Tuple, Optional
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import MD5

logger = logging.getLogger(__name__)


class CryptoJSAES:
    """兼容 crypto-js 的 AES 加密实现"""
    
    # crypto-js 使用的固定参数
    KEY_SIZE = 32  # 256 bits
    IV_SIZE = 16
    SALT_SIZE = 8
    ITERATIONS = 1  # crypto-js 默认使用 1 次迭代（不够安全，但兼容）
    
    def __init__(self, passphrase: str):
        """初始化
        
        Args:
            passphrase: 密码短语（与 crypto-js 中的 key 相同）
        """
        self.passphrase = passphrase.encode('utf-8')
    
    def _evp_kdf(self, salt: bytes) -> Tuple[bytes, bytes]:
        """EVP_BytesToKey 算法（OpenSSL 兼容）
        
        crypto-js 使用 MD5 作为哈希函数
        
        Args:
            salt: 8 字节 salt
            
        Returns:
            (key, iv) 元组
        """
        
        
        # 需要 32 字节密钥 + 16 字节 IV = 48 字节
        key_iv = b''
        prev = b''
        
        while len(key_iv) < 48:
            # MD5(prev + password + salt)
            hash_input = prev + self.passphrase + salt
            prev = MD5.new(hash_input).digest()
            key_iv += prev
        
        key = key_iv[:32]
        iv = key_iv[32:48]
        
        return key, iv
    
    def encrypt(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """加密数据（兼容 crypto-js 格式）
        
        Args:
            data: 要加密的数据字典
            
        Returns:
            (是否成功, 加密数据(base64), 错误信息)
        """
        try:
            # 1. JSON 序列化
            json_str = json.dumps(data, ensure_ascii=False)
            plaintext = json_str.encode('utf-8')
            logger.debug(f"Encrypting JSON: {json_str[:100]}...")
            
            # 2. 生成随机 salt
            salt = get_random_bytes(self.SALT_SIZE)
            
            # 3. 派生密钥和 IV
            key, iv = self._evp_kdf(salt)
            logger.debug(f"Key: {key.hex()[:32]}..., IV: {iv.hex()[:32]}...")
            
            # 4. 使用 AES-CBC 加密
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # 5. PKCS7 填充
            pad_length = AES.block_size - (len(plaintext) % AES.block_size)
            plaintext_padded = plaintext + bytes([pad_length] * pad_length)
            logger.debug(f"Plaintext: {len(plaintext)} bytes, padded: {len(plaintext_padded)} bytes")
            
            ciphertext = cipher.encrypt(plaintext_padded)
            
            # 6. 组合格式：Salted__ + salt + ciphertext
            # crypto-js 使用这个特定格式
            encrypted = b'Salted__' + salt + ciphertext
            
            # 7. Base64 编码
            encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
            
            logger.debug(f"Encrypted with crypto-js format: {len(encrypted_b64)} chars, prefix: {encrypted_b64[:20]}")
            return True, encrypted_b64, ""
        
        except Exception as e:
            msg = f"Encryption error: {str(e)}"
            logger.error(msg)
            return False, None, msg
    
    def decrypt(self, encrypted_b64: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """解密数据（兼容 crypto-js 格式）
        
        Args:
            encrypted_b64: Base64 编码的加密数据
            
        Returns:
            (是否成功, 解密数据字典, 错误信息)
        """
        try:
            logger.debug(f"Decrypting data (length: {len(encrypted_b64)}, prefix: {encrypted_b64[:20]})")
            
            # 1. Base64 解码
            encrypted = base64.b64decode(encrypted_b64)
            logger.debug(f"After base64 decode: {len(encrypted)} bytes")
            
            # 2. 检查是否有 "Salted__" 前缀
            if not encrypted.startswith(b'Salted__'):
                raise ValueError("Invalid crypto-js format: missing 'Salted__' prefix")
            
            # 3. 提取 salt 和 ciphertext
            salt = encrypted[8:16]  # 8 bytes salt
            ciphertext = encrypted[16:]
            logger.debug(f"Salt: {salt.hex()}, ciphertext: {len(ciphertext)} bytes")
            
            # 4. 派生密钥和 IV
            key, iv = self._evp_kdf(salt)
            logger.debug(f"Key: {key.hex()[:32]}..., IV: {iv.hex()[:32]}...")
            
            # 5. 使用 AES-CBC 解密
            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext_padded = cipher.decrypt(ciphertext)
            logger.debug(f"Decrypted (padded): {len(plaintext_padded)} bytes")
            
            # 6. 移除 PKCS7 填充
            pad_length = plaintext_padded[-1]
            plaintext = plaintext_padded[:-pad_length]
            logger.debug(f"After removing padding: {len(plaintext)} bytes, pad_length: {pad_length}")
            
            # 7. 解析 JSON
            json_str = plaintext.decode('utf-8')
            logger.debug(f"Decrypted JSON: {json_str[:100]}...")
            data = json.loads(json_str)
            
            logger.debug(f"Decrypted crypto-js format successfully")
            return True, data, ""
        
        except ValueError as e:
            msg = f"Decryption failed: {str(e)}"
            logger.warning(msg)
            return False, None, msg
        except Exception as e:
            msg = f"Decryption error: {str(e)}"
            logger.error(msg)
            return False, None, msg

