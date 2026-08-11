#!/usr/bin/env python3
"""
Slack 연동 로그 모니터링 시스템
사용법: 
1. 환경변수 설정: export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
2. 실행: python3 log_alert_slack.py /tmp/backend.log
"""

import sys
import time
import re
import os
import requests
from datetime import datetime

# Slack Webhook URL (환경변수에서 읽기)
SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK_URL')

# 알람 패턴 정의
ALERT_PATTERNS = {
    'auth_failed': r'401 Unauthorized',
    'forbidden': r'403 Forbidden',
    'not_found': r'404 Not Found',
    'server_error': r'50[0-9]',
    'critical': r'CRITICAL|FATAL',
    'error': r'ERROR'
}

def send_slack_alert(alert_type, message):
    """
    Slack으로 알람 전송
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 콘솔에도 출력
    print(f"\n{'='*60}")
    print(f"🚨 알람 발생: {alert_type}")
    print(f"시간: {timestamp}")
    print(f"메시지: {message[:100]}...")
    print(f"{'='*60}\n")
    
    # Slack 전송
    if not SLACK_WEBHOOK:
        print("⚠️  SLACK_WEBHOOK_URL 환경변수가 설정되지 않았습니다.")
        print("   설정 방법: export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'")
        return
    
    # 알람 타입별 색상 및 이모지
    alert_config = {
        'auth_failed': {'color': 'warning', 'emoji': '🔐'},
        'forbidden': {'color': 'danger', 'emoji': '⛔'},
        'not_found': {'color': 'warning', 'emoji': '❓'},
        'server_error': {'color': 'danger', 'emoji': '🔥'},
        'critical': {'color': 'danger', 'emoji': '💥'},
        'error': {'color': 'warning', 'emoji': '⚠️'}
    }
    
    config = alert_config.get(alert_type, {'color': 'warning', 'emoji': '🚨'})
    
    payload = {
        "text": f"{config['emoji']} 서버 알람: {alert_type}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{config['emoji']} {alert_type.upper()} 에러 감지"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*시간:*\n{timestamp}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*에러 타입:*\n{alert_type}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*로그:*\n```{message[:500]}```"
                }
            }
        ]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
        if response.status_code == 200:
            print("✅ Slack 알람 전송 성공")
        else:
            print(f"❌ Slack 알람 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Slack 알람 전송 중 오류: {e}")

def monitor_log(log_file):
    """
    로그 파일 실시간 모니터링
    """
    print(f"🔍 로그 모니터링 시작: {log_file}")
    print(f"감지 패턴: {list(ALERT_PATTERNS.keys())}")
    
    if SLACK_WEBHOOK:
        print("✅ Slack 연동 활성화")
    else:
        print("⚠️  Slack 연동 비활성화 (환경변수 미설정)")
    
    print("Ctrl+C로 중단\n")
    
    try:
        with open(log_file, 'r') as f:
            # 파일 끝으로 이동
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                # 패턴 매칭
                for alert_type, pattern in ALERT_PATTERNS.items():
                    if re.search(pattern, line):
                        send_slack_alert(alert_type, line.strip())
                        break
                
    except KeyboardInterrupt:
        print("\n✅ 모니터링 종료")
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {log_file}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = "/tmp/backend.log"
    
    monitor_log(log_file)
