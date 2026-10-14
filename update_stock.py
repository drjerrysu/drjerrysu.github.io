import json
import urllib.request
import datetime
import csv

today = datetime.date.today().strftime("%Y-%m-%d")

# 證交所公開資料集：三大法人買賣超日報的直接下載點（最穩定、不會被防爬蟲阻擋）
url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=csv"

# 模擬標準瀏覽器的完整 Headers
req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
)

stock_list = []

try:
    with urllib.request.urlopen(req, timeout=15) as response:
        # 嘗試用不同的編碼讀取
        raw_bytes = response.read()
        try:
            content = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = raw_bytes.decode('big5', errors='ignore')
            
        lines = content.splitlines()
        csv_reader = csv.reader(lines)
        
        for row in csv_reader:
            # 過濾並尋找有效的上市股票資料行
            if len(row) >= 16:
                code = row[0].strip().replace('=', '').replace('"', '')
                name = row[1].strip().replace('"', '')
                
                # 必須是 4 位純數字的股票代號
                if code.isdigit() and len(code) == 4:
                    try:
                        # 嚴格抓取三大法人買賣超張數欄位
                        # 欄位 [4]: 外陸資買賣超張數
                        # 欄位 [10]: 投信買賣超張數
                        # 欄位 [15]: 自營商買賣超張數
                        foreign = int(row[4].replace(',', '').replace('+', '').strip())
                        trust = int(row[10].replace(',', '').replace('+', '').strip())
                        self_amt = int(row[15].replace(',', '').replace('+', '').strip())
                        
                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                    except (ValueError, IndexError):
                        continue

    print(f"成功取得真實資料，共解析 {len(stock_list)} 筆股票")

except Exception as e:
    print(f"連線或解析發生例外: {e}")

# 防呆機制：若抓不到資料，印出警告但不讓整個 Action 直接崩潰，而是記錄錯誤日誌
if len(stock_list) == 0:
    print("警告：本次未能取得資料，保留舊檔或等待下一次盤後更新。")
    exit(0)

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print("成功寫入 stock_data.json！")
