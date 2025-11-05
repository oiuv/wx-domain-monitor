#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信域名拦截检测工具
单次检测版本
"""

import json
import requests
from urllib.parse import quote
import sys

# 导入配置文件
try:
    from config import WEBHOOK_URL
except ImportError:
    print("❌ 无法导入配置文件，请确保 config.py 存在")
    sys.exit(1)


def send_webhook_notification(url, result):
    """
    发送异常通知到企业微信群

    Args:
        url (str): 被检测的URL
        result (dict): 检测结果字典，包含code、msg和status字段
    """
    if result.get('status') != 'abnormal':
        # 只在异常情况下发送通知
        return

    try:
        # 获取当前时间
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 构造通知消息
        message = {
            "msgtype": "text",
            "text": {
                "content": f"🚨 微信域名拦截告警\n\n检测到域名被微信拦截：\nURL：{url}\n状态：{result.get('msg', '异常')}\n时间：{current_time}\n\n🔧 【开发调试消息】"
            }
        }

        # 发送请求
        response = requests.post(WEBHOOK_URL, json=message, timeout=5)

        if response.status_code == 200:
            result_data = response.json()
            if result_data.get('errcode') == 0:
                print(f"✅ 异常通知已发送到微信群")
            else:
                print(f"⚠️ 通知发送失败：{result_data.get('errmsg')}")
        else:
            print(f"⚠️ 通知发送失败，HTTP状态码：{response.status_code}")

    except Exception as e:
        print(f"⚠️ 通知发送异常：{str(e)}")


def check_wx_domain(url):
    """
    检测微信域名是否被封

    Args:
        url (str): 要检测的域名或URL

    Returns:
        dict: 从腾讯接口返回的原始响应数据，如果请求失败返回None
    """
    if not url:
        return None

    try:
        # 构建检测URL（腾讯官方接口）
        check_url = 'https://cgi.urlsec.qq.com/index.php?m=url&a=validUrl&url=' + quote(url)

        # 设置请求头
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # 发送请求
        response = requests.get(check_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except (requests.exceptions.Timeout, requests.exceptions.RequestException,
            json.JSONDecodeError, Exception):
        return None


def main():
    """主函数 - 交互式命令行版本"""
    print("=" * 50)
    print("微信域名拦截检测工具")
    print("=" * 50)

    while True:
        # 获取用户输入
        url = input("\n请输入要检测的域名或URL（输入'quit'退出）: ").strip()

        # 检查退出命令
        if url.lower() in ['quit', 'exit', 'q', '退出']:
            print("感谢使用！")
            break

        # 检查输入
        if not url:
            print("❌ 请输入有效的域名或URL")
            continue

        # 执行检测
        print(f"\n🔍 正在检测域名: {url}")
        print("-" * 50)

        result = check_wx_domain(url)

        # 输出原始响应（从腾讯接口返回的完整数据）
        print("📦 原始响应数据:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print()

        # 显示reCode状态码说明
        re_code = result.get('reCode', None)
        if re_code is not None:
            if re_code == -202:
                display_msg = result.get('data', '')
                print(f"✅ 正常 - {display_msg}")
            elif re_code == -203:
                display_msg = result.get('data', '')
                print(f"❌ 异常 - {display_msg}")
                # 发送微信群通知
                notification_result = {
                    'status': 'abnormal',
                    'msg': display_msg
                }
                send_webhook_notification(url, notification_result)
            elif re_code == 0:
                display_msg = "风险网址拦截，链接可能包含不安全的内容"
                print(f"❌ 异常 - {display_msg}")
                # 发送微信群通知
                notification_result = {
                    'status': 'abnormal',
                    'msg': display_msg
                }
                send_webhook_notification(url, notification_result)
            else:
                print(f"⚠️ 未知 - reCode: {re_code}, msg: {result.get('data', '')}")
        else:
            print("⚠️ 请求失败，无法获取数据")

        print("-" * 50)


if __name__ == "__main__":
    # 运行主函数
    main()
