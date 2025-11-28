"""Token 提取工具"""
from urllib.parse import unquote
from typing import Dict, Any, Optional


class TokenExtractor:
    """Token 提取器"""
    
    @staticmethod
    def extract_from_query_string(query_string: str) -> Optional[str]:
        """从查询字符串提取 token
        
        格式: ?token=xxx 或 ?auth=xxx
        支持 Bearer 前缀: ?token=Bearer xxx
        
        Args:
            query_string: QUERY_STRING
            
        Returns:
            token 或 None
        """
        if not query_string:
            return None
        
        # 解析查询参数
        params = {}
        for pair in query_string.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                # URL 解码 token 值
                params[key] = unquote(value)
        
        token = params.get('token') or params.get('auth')
        
        # 移除 Bearer 前缀（如果存在）
        if token and token.lower().startswith('bearer '):
            token = token[7:].strip()
        
        return token
    
    @staticmethod
    def extract_from_headers(headers: Dict[str, str]) -> Optional[str]:
        """从 HTTP 头部提取 token
        
        格式: Authorization: Bearer <token>
        
        Args:
            headers: HTTP 头字典
            
        Returns:
            token 或 None
        """
        auth_header = headers.get('authorization') or headers.get('Authorization')
        
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            return parts[1]
        
        return None
    
    @staticmethod
    def extract_from_auth(auth: Optional[Dict[str, Any]]) -> Optional[str]:
        """从 Socket.IO auth 对象提取 token
        
        格式: auth={'token': 'xxx'}
        
        Args:
            auth: Socket.IO auth 字典
            
        Returns:
            token 或 None
        """
        if not auth or not isinstance(auth, dict):
            return None
        
        token = auth.get('token')
        
        # 移除 Bearer 前缀（如果存在）
        if token and isinstance(token, str) and token.lower().startswith('bearer '):
            token = token[7:].strip()
        
        return token
    
    @staticmethod
    def extract_from_environ(environ: Dict[str, Any], auth: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """从 ASGI environ 或 auth 对象提取 token
        
        优先级：auth 对象 > headers > query string
        （Headers 优先于 Query String，因为更安全）
        
        Args:
            environ: ASGI environ 字典
            auth: Socket.IO auth 对象（可选）
            
        Returns:
            token 或 None
        """
        # 0. 优先从 Socket.IO auth 对象提取
        if auth:
            token = TokenExtractor.extract_from_auth(auth)
            if token:
                return token
        
        # 1. 从 HTTP 头提取（更安全）
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                headers[header_name] = value
        
        token = TokenExtractor.extract_from_headers(headers)
        if token:
            return token
        
        # 2. 从查询字符串提取（兼容性，但不推荐）
        query_string = environ.get('QUERY_STRING', '')
        token = TokenExtractor.extract_from_query_string(query_string)
        if token:
            return token
        
        return None

