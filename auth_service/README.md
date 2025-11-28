# 认证服务（开发测试）

模拟用户系统，用于开发和测试。**生产环境替换为真实用户服务（云端）**。

## 架构说明

```
前端 → Auth Service (3124) → 获取 Token
前端 → Backend (8000)       → 验证 Token (公钥)
```

- **Auth Service**: 负责用户认证，使用私钥签发 Token
- **Backend**: 仅验证 Token，使用公钥验证签名

## 快速开始

### 1. 生成 RSA 密钥对

```bash
cd auth_service
mkdir -p keys
cd keys

# 生成私钥（认证服务使用）
openssl genrsa -out private_key.pem 2048

# 生成公钥（Backend 使用）
openssl rsa -in private_key.pem -pubout -out public_key.pem

# 复制公钥到 Backend
mkdir -p ../../backend/keys
cp public_key.pem ../../backend/keys/
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动服务

```bash
python main.py
```

服务运行在 `http://localhost:3124`

## 测试用户

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| test_user | test123 | user | robot:control, robot:read |
| admin | admin123 | admin | * (全部权限) |
| robot_user | robot123 | operator | robot:control, robot:read, robot:upload |

## API 端点

### 用户登录

```bash
POST /auth/login
Content-Type: application/json

{
  "username": "test_user",
  "password": "test123"
}

# 响应
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "user_001",
  "username": "test_user"
}
```

### 刷新 Token

```bash
POST /auth/refresh
Content-Type: application/json

{
  "token": "old_token_here"
}
```

### 快速获取 Token（仅测试）

```bash
GET /auth/token/{username}

# 示例
curl http://localhost:3124/auth/token/test_user

# 响应
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "user_001",
  "username": "test_user"
}
```

**使用 Token 访问前端：**

```bash
# 1. 复制上面响应中的 access_token
# 2. 拼接到前端 URL 的 ?token= 参数
http://localhost:5173/?token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

# 3. 在浏览器中打开该 URL
# 4. 前端自动从 URL 读取 Token 并连接 Backend
```

### 获取公钥（供 Backend 使用）

```bash
GET /auth/public-key
```

### 列出测试用户

```bash
GET /auth/users
```

## 使用流程

### 开发测试

**步骤 1：启动服务**
```bash
# 终端 1 - 启动认证服务
cd auth_service
python main.py  # 端口 3124

# 终端 2 - 启动 Backend
cd backend
python main.py  # 端口 8000

# 终端 3 - 启动前端
cd frontend
npm run dev     # 端口 5173
```

**步骤 2：获取 Token**
```bash
# 使用 curl 获取 Token
curl http://localhost:3124/auth/token/test_user

# 复制响应中的 access_token
```

**步骤 3：访问前端**
```bash
# 在浏览器中打开（带 Token 参数）
http://localhost:5173/?token=你的access_token

# 前端会自动：
# 1. 从 URL 读取 Token
# 2. 使用 Token 连接 Backend (ws://host:8000?token=xxx)
# 3. Backend 使用公钥验证 Token
# 4. 建立加密通信（AES-256-GCM）
```

**简化说明：**
- ✅ Token 完全通过 URL 传递（无 localStorage）
- ✅ 加密默认启用（无需配置）
- ✅ 前端零配置（固定密钥）

### 生产环境

**替换为真实用户服务：**

1. 部署到云端
2. 连接真实数据库
3. 添加安全措施：
   - 密码加密（bcrypt）
   - 验证码
   - MFA 多因素认证
   - 限流
4. 移除测试端点（`/auth/token/{username}`, `/auth/users`）
5. 配置 HTTPS

## Token 格式

使用 RS256 签名的 JWT Token，包含以下声明：

```json
{
  "user_id": "user_001",
  "username": "test_user",
  "role": "user",
  "permissions": ["robot:control", "robot:read"],
  "iat": 1234567890,
  "exp": 1234571490,
  "iss": "robot-auth-service"
}
```

## 安全说明

⚠️ **重要提示：**

- 私钥（`private_key.pem`）仅存储在认证服务
- 公钥（`public_key.pem`）分发给需要验证 Token 的服务
- 生产环境必须使用 HTTPS
- 生产环境必须修改密钥对
- 生产环境必须连接真实数据库

## 故障排除

### 问题：连接被拒绝（错误码：00010）

**原因：** 缺少 Token

**解决：**
```bash
# 1. 确保 URL 包含 token 参数
http://localhost:5173/?token=你的token

# 2. 检查 token 是否在 URL 中
console.log(new URLSearchParams(window.location.search).get('token'))
```

### 问题：Token 无效（错误码：00011）

**原因：** Token 格式错误或签名验证失败

**解决：**
1. 确保公钥已复制到 Backend (`backend/keys/public_key.pem`)
2. 检查 `issuer` 是否一致（auth_service 和 backend 配置）
3. 重新获取 Token：`curl http://localhost:3124/auth/token/test_user`

### 问题：Token 已过期（错误码：00012）

**原因：** Token 超过有效期（默认 3600 秒）

**解决：**
```bash
# 方式 1：使用刷新端点
curl -X POST http://localhost:3124/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"token":"你的旧token"}'

# 方式 2：重新获取新 Token
curl http://localhost:3124/auth/token/test_user
```

### 问题：Backend 无法验证 Token

**解决：**
1. 确保公钥已复制：`ls backend/keys/public_key.pem`
2. 检查 Backend 配置：
   ```yaml
   security:
     public_key_path: "keys/public_key.pem"
     issuer: "robot-auth-service"  # 必须与 auth_service 一致
   ```
3. 查看 Backend 日志获取详细错误

## 文件结构

```
auth_service/
├── main.py              # 服务主程序
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖
├── keys/               # RSA 密钥对
│   ├── private_key.pem # 私钥（签发 Token）
│   └── public_key.pem  # 公钥（验证 Token）
└── README.md           # 本文件
```

## 连接错误码

| 错误码 | 说明 | 解决方法 |
|--------|------|----------|
| `00010` | 缺少 Token | 确保 URL 包含 `?token=xxx` 参数 |
| `00011` | Token 无效 | 检查公钥配置，重新获取 Token |
| `00012` | Token 过期 | 使用 `/auth/refresh` 刷新或重新获取 |

## 快速测试

```bash
# 一键获取并访问（macOS/Linux）
TOKEN=$(curl -s http://localhost:3124/auth/token/test_user | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "打开浏览器访问："
echo "http://localhost:5173/?token=$TOKEN"

# 或者直接打开（macOS）
open "http://localhost:5173/?token=$TOKEN"
```

## 相关文档

- [Backend README](../backend/README.md)
- [前端 README](../frontend/README.md)

