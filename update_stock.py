import json
import datetime
import subprocess
import sys

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# 自動往回推算最近幾個營業日（避開當日未結算或假日導致空資料）
target_date_str = ""
stock_list = []
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.twse.com.tw/'
}

session = requests.Session()

# 嘗試今天，若無資料則依序往前推算最多 5 天（抓取最近一個交易日）
for i in range(5):
    check_date = datetime.date.today() - datetime.timedelta(days=i)
    # 跳過週末
    if check_date.weekday() >= 5:
        continue
        
    date_str = check_date.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=all"
    
    print(f"嘗試抓取日期: {check_date.strftime('%Y-%m-%d')} ...")
    try:
        response = session.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data']:
                print(f"成功取得 {check_date.strftime('%Y-%m-%d')} 的真實資料！共 {len(data['data'])} 筆")
                target_date_str = check_date.strftime("%Y-%m-%d")
                
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
                break
    except Exception as e:
        print(f"連線錯誤: {e}")

if len(stock_list) == 0:
    raise ValueError("錯誤：連續嘗試多日仍無法取得證交所資料！")

output = {
    "date": target_date_str,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已成功寫入 {target_date_str} 的完整真實市場數據，共計 {len(stock_list)} 筆！")
