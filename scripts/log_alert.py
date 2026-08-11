#!/usr/bin/env python3
"""
로그 실시간 모니터링 및 알람 시스템
사용법: python log_alert.py <로그파일>
"""

import sys
import time
import re
from datetime import datetime

# 알람 설정
ERROR_CODES = [400, 401, 403, 404, 500, 502, 503]
ALERT_PATTERNS = {
    'auth_failed': r'401 Unauthorized',
    'forbidden': r'403 Forbidden',
    'not_found': r'404 Not Found',
    'server_error': r'50[0-9]',
    'critical': r'CRITICAL|FATAL',
    'error': r'ERROR'
}

def send_alert(alert_type, message):
    """
    알람 전송 (여기에 Slack, Email, SMS 로직 추가)
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n{'='*60}")
    print("🚨 알람 발생!")
    print(f"시간: {timestamp}")
    print(f"타입: {alert_type}")
    print(f"메시지: {message}")
    print(f"{'='*60}\n")
    
    # TODO: 실제 알람 전송
    # Slack 예시:
    # import requests
    # webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    # requests.post(webhook_url, json={"text": f"{alert_type}: {message}"})

def monitor_log(log_file):
    """
    로그 파일 실시간 모니터링
    """
    print(f"🔍 로그 모니터링 시작: {log_file}")
    print(f"감지 패턴: {list(ALERT_PATTERNS.keys())}")
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
                        send_alert(alert_type, line.strip())
                        break
                
    except KeyboardInterrupt:
        print("\n✅ 모니터링 종료")
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {log_file}")
        sys.exit(1)

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/backend.log"
    monitor_log(log_file)
