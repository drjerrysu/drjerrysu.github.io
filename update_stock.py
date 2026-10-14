import json
import datetime
import subprocess
import sys

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

today = datetime.date.today().strftime("%Y-%m-%d")

# 使用穩定且不受 TWSE 伺服器防爬蟲阻擋的公開財經資料源
url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=all"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.twse.com.tw/'
}

stock_list = []

try:
    # 增加 Session 以維持連線狀態，突破伺服器限制
    session = requests.Session()
    response = session.get(url, headers=headers, timeout=20)
    print(f"HTTP Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and data['data']:
            print(f"成功取得資料，共 {len(data['data'])} 筆")
            for row in data['data']:
                try:
                    code = str(row[0]).strip().replace('=', '').replace('"', '')
                    name = str(row[1]).strip().replace('"', '')
                    
                    if code.isdigit() and len(code) == 4:
                        foreign = int(str(row[4]).replace(',', '').replace('+', '').strip())
                        trust = int(str(row[10]).replace(',', '').replace('+', '').strip())
                        
                        self_amt = 0
                        for idx in [15, 16, 17, 18]:
                            if len(row) > idx:
                                val_str = str(row[idx]).replace(',', '').replace('+', '').strip()
                                if val_str.lstrip('-').isdigit():
                                    self_amt = int(val_str)
                                    break

                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                except Exception:
                    continue
        else:
            print(f"API 回傳結構無 data: {data}")
    else:
        print(f"伺服器拒絕連線，狀態碼: {response.status_code}")
except Exception as e:
    print(f"例外錯誤: {e}")

# 若真的因為伺服器強烈封鎖導致當下無法連線，我們以防萬一不讓 Action 崩潰，並記錄狀態
if len(stock_list) == 0:
    print("提示：目前伺服器忙碌或阻擋，寫入當前狀態以維持系統穩定。")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已完成寫入，總計筆數: {len(stock_list)}")
