import json
import urllib.request
import datetime
import csv
import io

today = datetime.date.today().strftime("%Y-%m-%d")

# 使用證交所三大法人買賣超日報的正確 CSV 匯出端點（最穩定、不會有 HTML 阻擋問題）
url = "https://www.twse.com.tw/rwd/zh/fund/T86?response=csv"

req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
)

stock_list = []

try:
    with urllib.request.urlopen(req) as response:
        # 證交所 CSV 通常是 Big5 編碼
        content = response.read().decode('big5', errors='ignore')
        lines = content.splitlines()
        
        # 過濾掉垃圾行，尋找含有資料的 CSV 行
        csv_reader = csv.reader(lines)
        for row in csv_reader:
            # 證交所 T86 CSV 欄位格式通常為：股票代號, 名稱, 外陸資買賣超張數, 投信買賣超張數, 自營商...
            if len(row) >= 15:
                code = row[0].strip().replace('"', '')
                name = row[1].strip().replace('"', '')
                
                # 檢查代號是否為有效股票 (通常為 4 位數字)
                if code.isdigit() and len(code) == 4:
                    try:
                        # 移除逗號
                        foreign = int(row[4].replace(',', '').strip())
                        trust = int(row[10].replace(',', '').strip())
                        self_amt = int(row[15].replace(',', '').strip())
                        
                        stock_list.append({
                            "code": code,
                            "name": name,
                            "foreign": foreign,
                            "trust": trust,
                            "self": self_amt
                        })
                    except ValueError:
                        continue

    print(f"成功從證交所抓取真實資料，共 {len(stock_list)} 筆")

except Exception as e:
    print(f"抓取失敗: {e}")

# 嚴格確保：如果抓不到資料，絕對不放假資料，而是拋出錯誤讓 Action 失敗，逼我們看清楚問題
if len(stock_list) == 0:
    raise ValueError("錯誤：無法取得證交所真實資料，已終止更新，絕不使用假資料！")

output = {
    "date": today,
    "data": stock_list
}

with open("stock_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print("已成功將 100% 真實證交所資料寫入 stock_data.json")
