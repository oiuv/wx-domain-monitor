#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信域名定时监测工具
每分钟自动检测域名列表中的域名状态
"""

import json
import requests
import time
from datetime import datetime
from urllib.parse import quote
import os
import sys

# 导入配置文件
try:
    from config import WEBHOOK_URL, NOTIFICATION_CONFIG, CHECK_INTERVAL, LOGS_DIR
except ImportError:
    print("❌ 无法导入配置文件，请确保 config.py 存在")
    sys.exit(1)

# 确保日志目录存在
os.makedirs(LOGS_DIR, exist_ok=True)


def load_domains():
    """
    加载域名列表（从domains.txt文件）
    每次检测前重新读取，支持热重载

    Returns:
        list: 域名列表
    """
    domains = []

    # 如果文件不存在，创建示例文件
    if not os.path.exists('domains.txt'):
        create_sample_domains_file()

    try:
        with open('domains.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if line and not line.startswith('#'):
                    domains.append(line)

        return domains
    except Exception as e:
        print(f"❌ 读取域名列表失败：{str(e)}")
        return []


def create_sample_domains_file():
    """
    创建示例域名列表文件
    """
    sample_domains = [
        "# 域名列表文件",
        "# 每行一个域名，以 # 开头的行为注释，会被跳过",
        "# 修改此文件后，下次检测周期将自动生效",
        "",
        "# 示例域名（请替换为实际需要监测的域名）",
        "# www.baidu.com",
        "# www.qq.com",
    ]

    with open('domains.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sample_domains))

    print("📝 已创建示例 domains.txt 文件，请编辑后重新运行程序")
    sys.exit(0)


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


def send_webhook_notification(url, result):
    """
    发送异常通知到企业微信群（复用 wx_domain_check.py 的通知逻辑）

    Args:
        url (str): 被检测的URL
        result (dict): 检测结果字典，包含code、msg和status字段
    """
    if result.get('status') != 'abnormal':
        return

    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = {
            "msgtype": "text",
            "text": {
                "content": f"🚨 微信域名拦截告警\n\n检测到域名被微信拦截：\nURL：{url}\n状态：{result.get('msg', '异常')}\n时间：{current_time}",
                **NOTIFICATION_CONFIG
            }
        }

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


def save_results(date_str, results):
    """
    保存检测结果到JSON日志文件

    Args:
        date_str (str): 日期字符串，格式：YYYY-MM-DD
        results (list): 检测结果列表
    """
    filename = os.path.join(LOGS_DIR, f"{date_str}.json")

    # 读取现有日志
    existing_logs = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_logs = json.load(f)
        except:
            existing_logs = []

    # 添加新的检测记录
    existing_logs.append({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'results': results
    })

    # 保存更新后的日志
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存日志失败：{str(e)}")


def run_monitor():
    """
    运行域名监控主循环
    """
    print("=" * 60)
    print("微信域名定时监测工具已启动")
    print(f"检测间隔：{CHECK_INTERVAL} 秒")
    print("按 Ctrl+C 可以停止程序")
    print("=" * 60)
    print()

    previous_status = {}  # 记录上次检测状态，用于状态变化检测

    while True:
        # 重新加载域名列表（支持热重载）
        domains = load_domains()

        if not domains:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ 没有找到需要检测的域名，请检查 domains.txt 文件")
            print(f"等待 {CHECK_INTERVAL} 秒后重试...\n")
            time.sleep(CHECK_INTERVAL)
            continue

        current_time = datetime.now()
        date_str = current_time.strftime('%Y-%m-%d')
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

        print(f"\n[{time_str}] 🔍 开始检测 {len(domains)} 个域名...")

        # 统计信息
        success_count = 0
        abnormal_count = 0
        unknown_count = 0

        # 检测结果列表
        batch_results = []

        # 检测每个域名
        for domain in domains:
            print(f"检测 {domain} ... ", end='', flush=True)

            result = check_wx_domain(domain)

            if result and isinstance(result, dict) and 'reCode' in result:
                # API调用成功
                re_code = result.get('reCode', None)
                data_msg = result.get('data', '')

                # 判断状态
                if re_code == -202:
                    print(f"✅ 正常 - {data_msg}")
                    success_count += 1
                elif re_code == -203:
                    display_msg = data_msg
                    print(f"❌ 异常 - {display_msg}")
                    abnormal_count += 1

                    # 每次检测到异常都发送通知
                    print(f"   💬 发送异常通知到微信群...")
                    send_webhook_notification(domain, {'status': 'abnormal', 'msg': display_msg})
                elif re_code == 0:
                    display_msg = '风险网址拦截，链接可能包含不安全的内容'
                    print(f"❌ 异常 - {display_msg}")
                    abnormal_count += 1

                    # 每次检测到异常都发送通知
                    print(f"   💬 发送异常通知到微信群...")
                    send_webhook_notification(domain, {'status': 'abnormal', 'msg': display_msg})
                else:
                    print(f"⚠️ 未知 - reCode: {re_code}, msg: {data_msg}")
                    unknown_count += 1

                # 记录结果
                batch_results.append({
                    'domain': domain,
                    'result': result,
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            else:
                # API调用失败
                print(f"❌ 请求失败")
                unknown_count += 1

                # 记录失败结果
                batch_results.append({
                    'domain': domain,
                    'result': None,
                    'error': 'API调用失败',
                    'time': datetime.now().strftime('%H:%M:%S')
                })

            # 避免请求过快
            time.sleep(0.5)

        # 统计信息
        print(f"\n📊 本次检测完成：")
        print(f"   ✅ 正常：{success_count} 个")
        print(f"   ❌ 异常：{abnormal_count} 个")
        print(f"   ⚠️ 未知：{unknown_count} 个")
        print()

        # 保存日志到文件
        save_results(date_str, batch_results)
        print(f"💾 检测日志已保存到 {LOGS_DIR}/{date_str}.json")

        print(f"\n⏱️ 等待 {CHECK_INTERVAL} 秒后进行下次检测...\n")
        print("-" * 60)
        print()

        # 等待下次检测
        time.sleep(CHECK_INTERVAL)


def main():
    """
    主函数
    """
    try:
        run_monitor()
    except KeyboardInterrupt:
        print("\n\n👋 程序已停止")
        print("感谢使用！")


if __name__ == "__main__":
    main()
