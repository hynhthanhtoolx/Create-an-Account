import os
import random
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent

user_agents = UserAgent()

CAU_HINH = {
    'DELAY_TOI_THIEU': 0.5,
    'DELAY_TOI_DA': 2.0,
    'SO_LAN_THU_LAI': 3,
    'THOI_GIAN_CHO_REQUEST': 30,
    'XOAY_USER_AGENT': True
}

def lay_user_agent_ngau_nhien():
    if CAU_HINH['XOAY_USER_AGENT']:
        return user_agents.random
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def kiem_tra_cookie(cookie):
    return all(f'{truong}=' in cookie for truong in ['c_user', 'xs'])

def lay_token(cookie, so_lan_thu=0):
    if not kiem_tra_cookie(cookie):
        return None
    headers = {
        'cookie': cookie,
        'user-agent': lay_user_agent_ngau_nhien()
    }
    try:
        response = requests.get(
            'https://business.facebook.com/content_management',
            headers=headers,
            timeout=CAU_HINH['THOI_GIAN_CHO_REQUEST']
        )
        response.raise_for_status()
        import re
        ket_qua = re.search(r'EAAG\w+', response.text)
        if ket_qua:
            return f'{cookie}|{ket_qua.group(0)}'
    except Exception:
        if so_lan_thu < CAU_HINH['SO_LAN_THU_LAI']:
            time.sleep(random.uniform(1, 3))
            return lay_token(cookie, so_lan_thu + 1)
    return None

def chia_se(tach, id_chia_se, so_lan_thu=0):
    if not tach or '|' not in tach:
        print(f"Share thất bại | ID: {id_chia_se}")
        return False
    cookie, token = tach.split('|', 1)
    headers = {
        'cookie': cookie,
        'user-agent': lay_user_agent_ngau_nhien()
    }
    link = random.choice([
        f'https://m.facebook.com/{id_chia_se}',
        f'https://www.facebook.com/{id_chia_se}'
    ])
    params = {
        'link': link,
        'published': 0, 
        'access_token': token,
        'fields': 'id'
    }
    try:
        res = requests.post(
            'https://graph.facebook.com/v15.0/me/feed',
            headers=headers,
            params=params,
            timeout=CAU_HINH['THOI_GIAN_CHO_REQUEST']
        )
        if res.status_code == 200 and res.json().get('id'):
            print(f"Share thành công | ID: {id_chia_se}")
            return True
        else:
            print(f"Share thất bại | ID: {id_chia_se}")
    except Exception:
        if so_lan_thu < CAU_HINH['SO_LAN_THU_LAI']:
            time.sleep(random.uniform(1, 3))
            return chia_se(tach, id_chia_se, so_lan_thu + 1)
        print(f"Share thất bại | ID: {id_chia_se}")
    return False

def run_tool(cookie, post_id, total_share=5, delay=1.0, threads=5):
    token = lay_token(cookie)
    if not token:
        print("Cookie không hợp lệ hoặc không lấy được token")
        return
    thanh_cong = 0
    that_bai = 0
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for _ in range(total_share):
            time.sleep(delay * random.uniform(0.8, 1.2))
            futures.append(executor.submit(chia_se, token, post_id))
        for f in as_completed(futures):
            if f.result():
                thanh_cong += 1
            else:
                that_bai += 1
    print("\n===== TỔNG KẾT =====")
    print(f"Thành công: {thanh_cong}")
    print(f"Thất bại: {that_bai}")

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    print("===== TOOL SHARE ẢO FACEBOOK BY HAIANH/d4gt201=====")
    cookie = input("Nhập cookie Facebook: ").strip()
    post_id = input("Nhập ID bài viết cần share: ").strip()
    try:
        total_share = int(input("Nhập số lần share (mặc định 5): ") or 5)
        delay = float(input("Nhập delay giữa các share (giây, mặc định 1.0): ") or 1.0)
        threads = int(input("Nhập số thread chạy cùng lúc (mặc định 5): ") or 5)
    except ValueError:
        total_share, delay, threads = 5, 1.0, 5

    print("\nĐang thực hiện share ảo, vui lòng chờ...\n")
    run_tool(cookie, post_id, total_share, delay, threads)
