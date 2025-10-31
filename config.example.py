#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信域名检测工具配置文件模板
复制此文件为 config.py 并填入实际配置
"""

# 企业微信机器人Webhook地址
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的机器人密钥"

# 需要通知的同事配置
NOTIFICATION_CONFIG = {
    # 用户ID列表（能正常@的同事）
    "mentioned_list": ["用户ID1", "用户ID2"],

    # 手机号列表（无法用用户ID@的同事）
    "mentioned_mobile_list": ["手机号1", "手机号2"]
}

# 检测间隔（秒）
CHECK_INTERVAL = 60

# 日志保存目录
LOGS_DIR = "logs"