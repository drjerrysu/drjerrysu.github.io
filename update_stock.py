import json
import datetime
import subprocess
import sys

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# 自動取得前一個交易日（避免當天收盤後資料尚未結算上架）
target_date = datetime.date.today() - datetime.timedelta(days=1)
if target_date.weekday() == 5:  # 星期六往前推到星期五
    target_date = target_date - datetime.timedelta(days=1)
elif target_date.weekday() == 6:  # 星期日往前推到星期五
    target_date = target_date - datetime.timedelta(days=2)

date_str = target_date.strftime("%Y%m%d")
print(f"指定抓取已結算之營業日資料: {target_date.strftime('%Y-%m-%d')}")

# 使用帶有明確日期的官方 JSON API 端點
url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=all"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.twse.com.tw/'
}

stock_list = []

try:
    response = requests.get(url, headers=headers, timeout=20)
    print(f"HTTP 狀態碼: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if 'data' in data and data['data']:
                print(f"成功取得真實資料，共 {len(data['data'])} 筆")
                for row in data['data']:
                    try:
                        code = str(row[0]).strip().replace('=', '').replace('"', '')
                        name = str(row[1]).strip().replace('"', '')
                        
                        if code.isdigit() and len(code) == 4:
                            foreign = int(str(row[4]).replace(',', '').replace('+', '').strip() or 0)
                            trust = int(str(row[10]).replace(',', '').replace('+', '').strip() or 0)
                            
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
                print(f"API 回傳訊息: {data.get('stat', '無資料')}")
        except json.JSONDecodeError:
            print(f"解析 JSON 失敗，伺服器可能回傳了 HTML 錯誤頁面。")
    else:
        print(f"請求失敗，狀態碼: {response.status_code}")
except Exception as e:
    print(f"發生例外錯誤: {e}")

output = {
    "date": target_date.strftime("%Y-%m-%d"),
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"已成功寫入 {len(stock_list)} 筆真實上市股票數據到 stock_data.json！")
