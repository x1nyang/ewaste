"""从闲鱼爬取PCB拆机料板图像"""

import requests
from bs4 import BeautifulSoup as bs
import hashlib
import time
import os
import uuid
import json

START_PAGE = 1
END_PAGE = 50

cookie = f't=b5d02f52068ae178a2c70048fc4fc73e; cna=RXnXIvhbiA4CATz/xb5Oc7gh; cookie2=1a7bccac012796309ae4e067484d5c77; mtop_partitioned_detect=1; _m_h5_tk=ec58071ad7f6f304eb0ec1325bc5a762_1790498317387; _m_h5_tk_enc=e0a08e3710664df610ac1c6651276e1b; _samesite_flag_=true; _tb_token_=71f13133a7673; xlly_s=1; tfstk=gcKifWgtcF7sDfNEqSSsGSf9GXgKfGsf1IEAMiCq865CMA1O6KRDnL726GITomv2_Z-OXddHmCdpBfOAXSmDt6dYDdKDRovWhhH1DAs6CisqwbnRid91cFnAjWGpLxWfmO5gQBKXCisqwKL3XXp6sA5UpiSqKMWV3lS4bikhLT1UbtrN3Wkhh6SVQiS2LWWAhtzV3IJEKt1Fgi7wgMkhh65V0ikpJo5k0HtESR-13kK2IHXGS_JnPorDXuQGad530b-hID1yQ6q40_OikIvHBfqWpG9eZTdtYlAkFHOhLQomtiOBuIWDT0NAfUd6VwvIzkJGj6_PUHk44sKMJL5hq-owKGfGzhQoqYAyKK8R-HHrVGjN_EI6H8c9KhA9CHvY3ySGXebkjgo7_sLpEnXDcjiHZLtBt9RrmfSPgyzrZcZfLxK3lr_Nd9f-0Tg6nz7-qBMnKzg1796twvD3lr_Nd9f-Kv471NWCBbC..'
_m_h5_tk = 'ec58071ad7f6f304eb0ec1325bc5a762'

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
    "Cookie":cookie,
    "Referer":"https://www.goofish.com/"
    }
headers2 = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
}

Search = "pcb"
save_path = r"E:\project\wpcbs\dataset\raw"
discription_path = r"E:\project\wpcbs\dataset\discription.json"

#获取签名
def get_sign(page_number):
    token = _m_h5_tk
    current_timestamp = int(time.time() * 1000)
    sixteen_hours_ago = current_timestamp - (16 * 60 * 60 * 1000)
    j = str(sixteen_hours_ago)
    h = '34839810'
    c_data = '{"pageNumber":%d,"keyword":"%s","fromFilter":false,"rowsPerPage":30,"sortValue":"","sortField":"","customDistance":"","gps":"","propValueStr":{},"customGps":"","searchReqFromPage":"pcSearch","extraFilterValue":"{}","userPositionJson":"{}"}' % (page_number, Search)

    string = token + "&" + j + "&" + h + "&" + c_data
    sign = hashlib.md5(string.encode('utf-8')).hexdigest()
    return j, c_data, sign

if os.path.exists(discription_path):
    with open(discription_path, "r", encoding="utf-8") as f:
        discription = json.load(f)
else:
    discription = []

for page in range(START_PAGE, END_PAGE+1):
    print(f"正在下载第{page}页数据")
    j, c_data, sign = get_sign(page)
    params = {
            "jsv": "2.7.2",
            "appKey": "34839810",
            "t": j,
            "sign": sign,
            "v": "1.0",
            "type": "originaljson",
            "accountSite": "xianyu",
            "dataType": "json",
            "timeout": "20000",
            "api": "mtop.taobao.idlemtopsearch.pc.search",
            "sessionOption": "AutoLoginOnly",
            "spm_cnt": "a21ybx.search.0.0",
            "spm_pre": "a21ybx.search.searchInput.0"
        }

    data = {'data':c_data}
    res = requests.post("https://h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search/1.0/",
                            headers=headers, params=params, data=data)
    json_data = res.json()
    try:
        resultList = json_data['data']['resultList']
    except Exception as e:
        print("检索网页失败，很可能是token过期")

    page_failed = 0
    for item in resultList:
        try:
            image_uuid = str(uuid.uuid4())
            image_url = item['data']['item']['main']['exContent']['picUrl']
            item_detail = item['data']['item']['main']['exContent']['detailParams']['title']
            image_res = requests.get(image_url, headers=headers2)
            image_path = os.path.join(save_path, image_uuid + '.jpg')
            image_detail = {
                "image_uuid":image_uuid,
                "detail":item_detail.replace('\n','').replace('"','*')
                }
            discription.append(image_detail)
            with open(image_path,'wb') as f:
                f.write(image_res.content)
            with open(discription_path, "w", encoding="utf-8") as f:
                json.dump(discription, f, ensure_ascii=False, indent=4)
        except Exception as e:
            page_failed += 1
    print(f"第{page}页数据下载完成，共{len(resultList)}条，失败{page_failed}条")