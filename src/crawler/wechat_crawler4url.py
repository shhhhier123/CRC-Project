
# -*- coding: UTF-8 -*-
import argparse as args
import requests
import time
import pandas as pd
import math
import random
import os
import csv
import numpy as np
import pickle


def write_to_excel(words, filename, sheet_name='sheet1'):
    words.to_excel(filename, sheet_name=sheet_name, index=False)


def append_to_excel(words, filename, sheet_name='sheet1'):
    last_data = pd.read_excel(filename)
    words = pd.concat([last_data, words])
    words.to_excel(filename, sheet_name=sheet_name, index=False)


if __name__ == "__main__":
    parser = args.ArgumentParser("wechat_crawler4url")
    parser.add_argument("--data_file", type = str, default = './data/url.xlsx')
    parser.add_argument("--ckpt_file", type=str, default='./data/ckpt.pkl')
    args = parser.parse_args()

    user_agent_list = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/45.0.2454.85 Safari/537.36 115Browser/6.0.3',
        'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
        'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
        'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0',
        'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Mobile Safari/537.36",
    ]

    # 目标url
    url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
    cookie = "appmsglist_action_3862699157=card; pgv_pvid=6866189676; fqm_pvqid=45797c1a-d2db-4477-94fe-722dabc1958a; RK=/f/YtMInEU; ptcz=4b55a93fe942541d8ab5aa9e52ade18648863d8c4fe9b580bf942573008e25e3; ua_id=6miidEgEdm6ZvQLMAAAAAPOOYzjhsBQpKhw4Q9yHnxU=; wxuin=31894540285984; mm_lang=zh_CN; _clck=13fg6n9|1|fr3|0; uuid=00fa1d197d5cf016578a2232b59a0969; rand_info=CAESIEDrRwiceGWO5Lp0/tkFtfR88aNgz7oZ0Sstmfy49VAZ; slave_bizuin=3862699157; data_bizuin=3862699157; bizuin=3862699157; data_ticket=Om2buwnZxWn/lfclikQnqWNE1A6KxWjxHF57jna4eiME4M34LlW6/S0FRZx84+MH; slave_sid=TEFmU2pKQnJIRFZGaDBLVGNGOE9PWWpWdlBqdnFEdzVQNXQzS2JtdUhJd2xabnhybW9qWThXSG1XaEFEWEVGbUlDaXQ2TThIcG5LaFFpeDI1QUlSeVpuQmVBTnQxaTBWQzBTeG42bUJ3aUNCc0xlMXE0blhTUE5SU2tybHVMSmNGWUJSbHVISE1tTWZFaUdL; slave_user=gh_268fee925581; xid=89f823b54c9186af1ddc9be73ed64140; _clsk=1e4r7cj|1732236182786|3|1|mp.weixin.qq.com/weheat-agent/payload/record"

    # 使用Cookie，跳过登陆操作

    data = {
        "token": "346703374",
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
        "action": "list_ex",
        "begin": "0",
        "count": "5",
        "query": "",
        "fakeid": "MjM5MTcxODgxNA==",
        "type": "9",
    }
    headers = {
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Mobile Safari/537.36",

        }
    content_json = requests.get(url, headers=headers, params=data).json()
    count = int(content_json["app_msg_cnt"])
    print(count)
    page = int(math.ceil(count / 5))
    print(page)
    content_list = []
    # 功能：爬取IP存入ip_list列表

    start_pt = 0

    if os.path.exists(args.ckpt_file):
        with open(args.ckpt_file, 'rb') as file:
            start_pt = pickle.load(file)

    for i in range(start_pt, page):
        data["begin"] = i * 5
        user_agent = random.choice(user_agent_list)
        headers = {
            "Cookie": cookie,
            "User-Agent": user_agent,

        }
        ip_headers = {
            'User-Agent': user_agent
        }
        # 使用get方法进行提交
        content_json = requests.get(url, headers=headers, params=data).json()
        # 返回了一个json，里面是每一页的数据
        for item in content_json["app_msg_list"]:
            # 提取每页文章的标题及对应的url
            items = []
            items.append(item["title"])
            items.append(item["link"])
            t = time.localtime(item["create_time"])
            items.append(time.strftime("%Y-%m-%d %H:%M:%S", t))
            content_list.append(items)
        print(i)
        if (i >= 0) and (i % 10 == 0):
            name = ['title', 'link', 'create_time']

            if not os.path.exists(args.data_file):
                test = pd.DataFrame(columns=name, data=content_list)
                write_to_excel(words=test, filename=args.data_file)
            else:
                test = pd.DataFrame(columns=name, data=content_list)
                append_to_excel(words=test, filename=args.data_file)
            print("第" + str(i) + "次保存成功")
            with open(args.ckpt_file, 'wb') as file:
                pickle.dump(i + 1, file)
            content_list = []
            time.sleep(random.randint(60,90))
        else:
            time.sleep(random.randint(15,25))

    name = ['title', 'link', 'create_time']
    test = pd.DataFrame(columns=name, data=content_list)
    test.to_excel(args.data_file, sheet_name='sheet1', index=False)
    print("最后一次保存成功")
