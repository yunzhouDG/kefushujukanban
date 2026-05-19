#!/usr/bin/env python3
"""
embed_and_push.py
将 build_cc_dashboard.py 生成的 cc_dashboard_data.json 加密后写入 dashboard_data.enc，
并更新 index.html 中的 dataVersion，然后推送到 GitHub（yunzhoudg.github.io/kefushujukanban）

用法：
    python embed_and_push.py [--no-push]
"""

import os
import re
import sys
import subprocess
import json
from datetime import datetime

# ========== 配置 ==========
WORK_DIR = r"c:\Users\EDY\WorkBuddy\20260427091108\cc-dashboard-github"
BUILD_DIR = r"c:\Users\EDY\WorkBuddy\20260423140754"
HTML_FILE = os.path.join(WORK_DIR, "index.html")
DATA_FILE = os.path.join(BUILD_DIR, "cc_dashboard_data.json")
ENC_FILE = os.path.join(WORK_DIR, "dashboard_data.enc")
PASSWORD = "Dg@2026kefu#kanban"

# GitHub repo 配置
REPO_DIR = WORK_DIR
REMOTE_NAME = "origin"
BRANCH = "main"  # GitHub Pages 部署的是 main 分支

# ========== 加密函数 ==========
from Crypto.Hash import SHA256

def derive_key(password: str, salt: bytes, iterations: int = 100000) -> bytes:
    """使用 PBKDF2 从密码派生密钥（与前端 Web Crypto API 一致：HMAC-SHA256）"""
    from Crypto.Protocol.KDF import PBKDF2
    return PBKDF2(password.encode('utf-8'), salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)

def encrypt_data(data: str, password: str) -> str:
    """使用 AES-CBC 加密数据（与前端 Web Crypto API 一致）
    前端参数：PBKDF2(salt='dashboard', iterations=10000, hash=SHA-256) + AES-CBC(iv=16bytes)
    输出格式：base64(iv + ciphertext)
    """
    from Crypto.Cipher import AES
    import base64
    import os

    # 前端 salt 是字符串 'dashboard' 的 UTF-8 编码，不是随机 salt
    salt = b'dashboard'
    key = derive_key(password, salt, iterations=10000)

    # 生成随机 IV（16字节，AES块大小）
    iv = os.urandom(16)

    # AES-CBC 加密
    cipher = AES.new(key, AES.MODE_CBC, iv)
    data_bytes = data.encode('utf-8')

    # PKCS7 填充
    pad_len = 16 - (len(data_bytes) % 16)
    data_bytes += bytes([pad_len]) * pad_len

    ciphertext = cipher.encrypt(data_bytes)

    # 组合: IV + ciphertext，然后 base64 编码
    combined = iv + ciphertext
    return base64.b64encode(combined).decode('utf-8')

# ========== 主流程 ==========
def main():
    no_push = "--no-push" in sys.argv

    # 1. 读取 cc_dashboard_data.json
    print(f"[1/4] 读取数据文件: {DATA_FILE}")
    if not os.path.exists(DATA_FILE):
        print(f"  ERROR: 数据文件不存在: {DATA_FILE}")
        print(f"  请先运行 build_cc_dashboard.py")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = f.read()

    # 检查数据有效性
    try:
        json.loads(raw_data)
        print(f"  数据校验通过，大小: {len(raw_data):,} 字节")
    except json.JSONDecodeError as e:
        print(f"  WARNING: JSON 解析失败: {e}")

    # 2. 加密数据
    print(f"[2/4] 加密数据...")
    encrypted = encrypt_data(raw_data, PASSWORD)
    print(f"  加密完成，密文大小: {len(encrypted):,} 字符")

    # 3. 写入 dashboard_data.enc（纯密文，供 index.html fetch 加载）
    print(f"[3/4] 写入 {ENC_FILE}")
    with open(ENC_FILE, "w", encoding="utf-8") as f:
        f.write(encrypted)
    print(f"  写入成功，大小: {len(encrypted):,} 字符")

    # 4. 更新 index.html 中的 dataVersion
    print(f"[4/5] 更新 index.html 版本号...")
    if not os.path.exists(HTML_FILE):
        print(f"  ERROR: HTML 文件不存在: {HTML_FILE}")
        sys.exit(1)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 更新 dataVersion
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    new_version = f"window.dataVersion = '{timestamp}';"
    pattern = r'window\.dataVersion\s*=\s*[^;]+;'
    new_html, n = re.subn(pattern, new_version, html_content)
    if n > 0:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"  版本号更新为: {timestamp}")
    else:
        print("  WARNING: 未找到 dataVersion，跳过")

    # 5. Git 推送
    if no_push:
        print("[5/5] 跳过 Git 推送 (--no-push)")
    else:
        print(f"[5/5] Git 推送到 {BRANCH} 分支...")
        os.chdir(REPO_DIR)

        # 确保在正确的分支
        subprocess.run(["git", "checkout", BRANCH], check=False)

        # 检查 git 状态
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not result.stdout.strip():
            print("  没有变更，跳过提交")
        else:
            # 设置代理
            subprocess.run(["git", "config", "http.proxy", "http://127.0.0.1:7897"], check=False)
            subprocess.run(["git", "config", "https.proxy", "http://127.0.0.1:7897"], check=False)

            # 添加文件（index.html + dashboard_data.enc）
            subprocess.run(["git", "add", "index.html", "dashboard_data.enc"], check=True)

            # 提交
            timestamp_display = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_msg = f"Update dashboard data {timestamp_display}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)

            # 推送
            subprocess.run(["git", "push", REMOTE_NAME, BRANCH], check=True)
            print(f"  推送成功: {commit_msg}")

    print("\n完成！")
    print(f"看板地址: https://yunzhoudg.github.io/kefushujukanban/")

if __name__ == "__main__":
    main()
