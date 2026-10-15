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
stock_list = []

# 我們改用證交所公開資料集的備用直連端點或 FinMind/Fugle 風格的穩定開源 API 鏡像
# 這裡使用證交所 OpenAPI 的固定對應格式，並加上更完整的 headers 與降級備用機制
urls = [
    "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=all",
    "https://openapi.twse.com.tw/v1/fund/T86" # 證交所官方 OpenAPI 專用端點
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Referer': 'https://www.twse.com.tw/'
}

session = requests.Session()
success = False

for url in urls:
    try:
        print(f"嘗試連線端點: {url}")
        res = session.get(url, headers=headers, timeout=20)
        print(f"HTTP 狀態碼: {res.status_code}")
        
        if res.status_code == 200:
            content_type = res.headers.get('Content-Type', '')
            if 'application/json' in content_type or res.text.startswith('[') or res.text.startswith('{'):
                data = res.json()
                
                # 處理證交所 rwd 格式
                rows = []
                if isinstance(data, dict):
                    if 'data' in data and data['data']:
                        rows = data['data']
                elif isinstance(data, list):
                    rows = data
                
                if rows:
                    print(f"成功從端點取得資料，共 {len(rows)} 筆")
                    for row in rows:
                        try:
                            # 兼容不同 API 欄位對應 (rwd 陣列 vs OpenAPI 字典)
                            if isinstance(row, dict):
                                code = str(row.get('StkNo', row.get('code', ''))).strip().replace('=', '').replace('"', '')
                                name = str(row.get('StkName', row.get('name', ''))).strip().replace('"', '')
                                foreign = int(str(row.get('ForeignInvestmentNetBuySell', row.get('foreign', 0))).replace(',', '').replace('+', '').strip())
                                trust = int(str(row.get('InvestmentTrustNetBuySell', row.get('trust', 0))).replace(',', '').replace('+', '').strip())
                                self_amt = int(str(row.get('DealerNetBuySell', row.get('self', 0))).replace(',', '').replace('+', '').strip())
                            else:
                                # 傳統 rwd list 格式
                                code = str(row[0]).strip().replace('=', '').replace('"', '')
                                name = str(row[1]).strip().replace('"', '')
                                foreign = int(str(row[4]).replace(',', '').replace('+', '').strip())
                                trust = int(str(row[10]).replace(',', '').replace('+', '').strip())
                                self_amt = 0
                                for idx in [15, 16, 17, 18]:
                                    if len(row) > idx:
                                        val_str = str(row[idx]).replace(',', '').replace('+', '').strip()
                                        if val_str.lstrip('-').isdigit():
                                            self_amt = int(val_str)
                                            break

                            if code.isdigit() and len(code) == 4:
                                stock_list.append({
                                    "code": code,
                                    "name": name,
                                    "foreign": foreign,
                                    "trust": trust,
                                    "self": self_amt
                                })
                        except Exception:
                            continue
                            
                    if len(stock_list) > 0:
                        success = True
                        break
        else:
            print(f"此端點無法連線，跳過。")
    except Exception as e:
        print(f"請求發生錯誤: {e}")

if not success or len(stock_list) == 0:
    raise ValueError("錯誤：所有官方與鏡像 API 端點皆被伺服器阻擋或查無資料！")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print(f"完美寫入 stock_data.json！總計真實股票筆數: {len(stock_list)}")
