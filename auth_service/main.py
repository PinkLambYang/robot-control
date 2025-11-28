"""
独立认证服务 - 模拟用户系统（开发测试用）
生产环境替换为真实用户服务

端口: 3124
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import yaml
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
import uvicorn
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Auth Service (Dev/Test)", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载配置
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# 加载密钥
private_key_path = os.path.join(os.path.dirname(__file__), config['jwt']['private_key_path'])
public_key_path = os.path.join(os.path.dirname(__file__), config['jwt']['public_key_path'])

with open(private_key_path, 'r') as f:
    PRIVATE_KEY = f.read()

with open(public_key_path, 'r') as f:
    PUBLIC_KEY = f.read()


# ============ 数据模型 ============

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str
    username: str

class RefreshRequest(BaseModel):
    token: str


# ============ 模拟用户数据库 ============
# 生产环境：替换为真实数据库查询

MOCK_USERS = {
    "test_user": {
        "password": "test123",
        "user_id": "user_001",
        "role": "user",
        "permissions": ["robot:control", "robot:read"]
    },
    "admin": {
        "password": "admin123",
        "user_id": "admin_001",
        "role": "admin",
        "permissions": ["*"]
    },
    "robot_user": {
        "password": "robot123",
        "user_id": "robot_001",
        "role": "operator",
        "permissions": ["robot:control", "robot:read", "robot:upload"]
    }
}


# ============ 认证逻辑 ============

def verify_user(username: str, password: str) -> Optional[Dict]:
    """验证用户（模拟）"""
    user = MOCK_USERS.get(username)
    if user and user['password'] == password:
        return user
    return None


def generate_token(user_id: str, username: str, user_data: Dict):
    """生成 JWT Token（使用私钥签名）"""
    expire_seconds = config['jwt']['expire_seconds']
    
    payload = {
        'user_id': user_id,
        'username': username,
        'role': user_data.get('role'),
        'permissions': user_data.get('permissions', []),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(seconds=expire_seconds),
        'iss': config['jwt']['issuer']  # 签发者
    }
    
    token = jwt.encode(payload, PRIVATE_KEY, algorithm='RS256')
    return token, expire_seconds


def verify_token(token: str):
    """验证 Token（使用公钥）"""
    try:
        payload = jwt.decode(
            token, 
            PUBLIC_KEY, 
            algorithms=['RS256'],
            issuer=config['jwt']['issuer']
        )
        return True, payload, ""
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
    except jwt.InvalidTokenError as e:
        return False, None, "Invalid token: {}".format(str(e))


# ============ API 端点 ============

@app.get("/")
async def root():
    """服务信息"""
    return {
        "service": "Authentication Service (Dev/Test)",
        "version": "1.0.0",
        "status": "running",
        "port": config['server']['port'],
        "note": "This is a mock service for development. Replace with production auth service."
    }


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录（获取Token）
    
    示例：
    POST /auth/login
    {
        "username": "test_user",
        "password": "test123"
    }
    """
    user = verify_user(request.username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token, expires_in = generate_token(user['user_id'], request.username, user)
    
    logger.info("Login successful: %s (user_id: %s)", request.username, user['user_id'])
    
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user_id=user['user_id'],
        username=request.username
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(request: RefreshRequest):
    """刷新Token
    
    POST /auth/refresh
    {
        "token": "old_token_here"
    }
    """
    valid, payload, error = verify_token(request.token)
    
    if not valid:
        raise HTTPException(status_code=401, detail=error)
    
    # 重新生成Token
    user_id = payload['user_id']
    username = payload['username']
    user = MOCK_USERS.get(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_token, expires_in = generate_token(user_id, username, user)
    
    logger.info("Token refreshed: %s", username)
    
    return TokenResponse(
        access_token=new_token,
        expires_in=expires_in,
        user_id=user_id,
        username=username
    )


@app.get("/auth/token/{username}")
async def quick_token(username: str):
    """快速获取Token（仅开发测试）
    
    GET /auth/token/test_user
    """
    user = MOCK_USERS.get(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    token, expires_in = generate_token(user['user_id'], username, user)
    
    logger.info("Quick token generated: %s", username)
    
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user_id": user['user_id'],
        "username": username,
        "note": "For development only"
    }


@app.get("/auth/public-key")
async def get_public_key():
    """获取公钥（供Backend使用）"""
    return {
        "public_key": PUBLIC_KEY,
        "algorithm": "RS256",
        "issuer": config['jwt']['issuer'],
        "note": "Use this public key to verify JWT tokens"
    }


@app.post("/auth/verify")
async def verify_token_endpoint(authorization: Optional[str] = Header(None, alias="Authorization")):
    """验证 Token（从 Authorization header）
    
    请求头：
    Authorization: Bearer <token>
    
    返回：
    {
        "user_id": "user_001",
        "username": "test_user",
        "role": "user",
        "permissions": [...],
        "iat": 1234567890,
        "exp": 1234571490,
        "iss": "robot-control-system"
    }
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization[7:].strip()  # 移除 "Bearer " 前缀并去除空格
    valid, payload, error = verify_token(token)
    
    if not valid:
        raise HTTPException(status_code=401, detail=error)
    
    logger.info("Token verified: %s", payload.get('username'))
    
    return payload


@app.get("/auth/users")
async def list_users():
    """列出所有测试用户（仅开发）"""
    return {
        "users": [
            {
                "username": username,
                "user_id": user['user_id'],
                "role": user['role'],
                "password": user['password'],
                "note": "For testing only"
            }
            for username, user in MOCK_USERS.items()
        ],
        "note": "These are mock users for development only"
    }


if __name__ == "__main__":
    port = config['server']['port']
    host = config['server']['host']
    
    logger.info("=" * 60)
    logger.info("🔐 Auth Service (Dev/Test) Starting...")
    logger.info("=" * 60)
    logger.info("Port: %s", port)
    logger.info("Test Users: %s", list(MOCK_USERS.keys()))
    logger.info("Endpoints:")
    logger.info("  - POST /auth/login")
    logger.info("  - POST /auth/refresh")
    logger.info("  - GET  /auth/token/{username}")
    logger.info("  - GET  /auth/public-key")
    logger.info("  - GET  /auth/users")
    logger.info("=" * 60)
    
    uvicorn.run(app, host=host, port=port, log_level="info")

