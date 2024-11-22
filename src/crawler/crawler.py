"""
@Function:          Crawl html
@Author:            Wangzhusong Zhang
@Last Update:       2024-11-05
@Coding Scheme:     utf-8
@Python Version:    python3.12
@Interpreter Name:  PyCharm
@Environment:       Anaconda
@Version:           0.2.0
@Note:              </>
"""
from requests.exceptions import RequestException
from urllib.parse import urlparse
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pandas as pd
import argparse
import requests
import pymysql
import pickle
import shutil
import redis
import time
import os
import utils


def crawl_html(args, url, headers: {str: str}, timeout=None):
    """
    尝试从指定的URL获取文档内容，支持重试机制。

    Args:

        args: 配置信息。

        url: 要访问的URL地址。

        headers: 请求头信息，字典类型，键和值都是字符串。

        timeout: 请求超时时间（秒），可选参数。

    Returns:

        如果成功获取到文档内容，则返回文档内容的字符串；否则返回None。

    """
    reconnect_cnt = 0

    while reconnect_cnt < args.MAX_RECONNECT_CNT:
        try:
            """
            r = requests.get(url, headers=headers, timeout=args.timeout)
            if r.status_code != 200:
                if r.status_code >= 400:
                    return None
                print(f"For url: {url}, having\n"
                      f"Stat {r.status_code}, a network or connection failure happened.\n"
                      f"Please try again...\n")
                time.sleep(1)
                reconnect_cnt += 1
            else:
                r.encoding = 'UTF-8'
                return r.text
            """
            return utils.selenium_crawling(url)


        except RequestException as e:
            print(f"For url: {url}, having\n"
                  f"RequestException: {e}\n")
            # time.sleep(1)
            # reconnect_cnt += 1
            break

    print("Retries exceeded the limit and could not fetch the HTML content.")
    return None


def crawl_all_urls(HtmlDoc, url):
    """
    从给定的HTML文档中提取并规范化所有链接的URL。

    Args:

        HtmlDoc: 包含HTML内容的字符串或类似文件的对象。

        url: 当前HTML文档的基础URL，用于解析相对URL。

    Returns:

        一个集合，包含所有提取并规范化后的URL。

    """
    domain = urlparse(url).netloc
    all_urls = set()

    try:
        soup = BeautifulSoup(HtmlDoc, 'html.parser')

    except TypeError:
        print("Fail to parse the html document! Error happened in", url)
        return all_urls

    for anchor in soup.find_all('a'):
        href = anchor.attrs.get("href")
        if href != "" and href is not None:
            href = href.strip()
            if not href.startswith('http'):
                href = urljoin(url, href)
                href = utils.checkio(href)
            else:
                href = utils.checkio(href)

            if domain in href and href != url:
                all_urls.add(href)

    return all_urls


def saving_in_redis(r, key, val):
    r.set(key, val)
    print(">Redis:")
    print(f"KEY:{key}")
    print(f"VAL:{val[:30]}")


def crawler(queue, args, cursor):
    """
    网络爬虫的主函数，用于从队列中逐个抓取URL，并处理抓取到的HTML文档。

    Args:

        queue (list): 待抓取的URL队列。

        args (argparse.Namespace): 配置信息。

        cursor (sqlite3.Cursor): 数据库游标，用于执行SQL语句。

    Returns:

    """
    sub_folder = None  # 用于存储HTML文档的子文件夹路径

    # 检查是否存在检查点文件，如果存在则加载队列和文件索引
    if os.path.exists(args.DataPath + "crawler_ckpt.pkl"):
        with open(args.DataPath + "crawler_ckpt.pkl", 'rb') as pickled:
            queue, file_index = pickle.load(pickled)

        # 根据文件索引生成数据库索引，并创建相应的子文件夹（如果需要）
        db_index = args.db_size.format(file_index)
        if file_index % args.SUBPAGE_SIZE == 0:
            sub_folder = args.HtmlPath + db_index
            if not os.path.exists(sub_folder):
                os.makedirs(sub_folder)
            sub_folder = sub_folder + "/"
        else:
            # 如果不是每args.SUBPAGE_SIZE个文件的索引，则使用前一个的索引作为文件夹名
            sub_folder = args.HtmlPath + args.db_size.format(int(file_index / args.SUBPAGE_SIZE) * args.SUBPAGE_SIZE)
            if not os.path.exists(sub_folder):
                os.makedirs(sub_folder)
            sub_folder = sub_folder + "/"
    else:
        file_index = 0  # 如果没有检查点文件，则文件索引从0开始

    # 打印爬虫开始信息
    print(f"Crawler started. Totally {len(queue)} url(s) in queue to crawl.")

    # 设置要忽略的文件扩展名集合
    extensions = set()
    for elem in [".jpg", ".jpeg", ".gif", ".png",
                 ".xls", ".xlsx", ".csv",
                 ".docx", ".doc",  ".pdf",
                 ".ppt", ".pptx",
                 ".zip", ".7z", ".rar",
                 ".mp3", ".wav", ".flac",
                 ".mp4", ".avi", ".mkv",
                 ".sql", ".obj", ".fbx", ".stl",
                 ".css", ".php"]:
        extensions.add(elem)
    del elem

    # 循环抓取队列中的URL，直到队列为空
    while len(queue) > 0:
        url = queue.pop(0)  # 从队列中取出一个URL
        time.sleep(args.pause_time)  # 暂停时长以避免请求过于频繁

        # 如果URL的文件扩展名在忽略列表中，则跳过该URL
        if os.path.splitext(url)[1] in extensions:
            continue

        # 抓取HTML文档
        html_doc = crawl_html(args, url, headers=args.headers)
        if html_doc is None:
            continue  # 如果抓取失败，则跳过该URL

        # redis数据库存储数据
        if args.output_mode == "redis":
            database = redis.Redis(host=args.redis_host, port=args.redis_port, db=args.redis_db)
            html_doc_extracted = utils.extract_main_text_from_html(html_doc)
            # print(url)
            # print(html_doc_extracted)
            # print(html_doc)
            saving_in_redis(database, url ,html_doc_extracted)

        if args.output_mode != "redis":
            # 计算HTML文档的哈希值
            hash_val = str(hash(html_doc))

            # 检查数据库中是否已存在该哈希值或URL的记录
            sql = f"SELECT * FROM {args.target_table} WHERE page_hash = '{hash_val}';"
            cursor.execute(sql)
            query_hash = cursor.fetchall()

            sql = f"SELECT * FROM {args.target_table} WHERE page_url = '{url}';"
            cursor.execute(sql)
            query_url = cursor.fetchall()
            if query_hash or query_url:
                continue  # 如果已存在，则跳过该URL

            # 从HTML文档中提取所有URL，并检查哪些是新URL（即数据库中不存在的URL）
            if not args.single_page_mode:
                url_sets = crawl_all_urls(html_doc, url)
                for new_url in url_sets:
                    sql = f"SELECT * FROM {args.target_table} WHERE page_url = '{new_url}';"
                    cursor.execute(sql)
                    query_url = cursor.fetchall()
                    if not query_url:
                        queue.insert(0, new_url)  # 将新URL插入队列开头以便后续抓取

            # 生成数据库索引，并准备存储HTML文档的路径
            db_index = args.db_size.format(file_index)
            if file_index % args.SUBPAGE_SIZE == 0:
                sub_folder = args.HtmlPath + db_index
                if not os.path.exists(sub_folder):
                    os.makedirs(sub_folder)
                sub_folder = sub_folder + "/"

            path = sub_folder + db_index + ".htm"  # 存储HTML文档的完整路径
            with open(path, 'w', encoding='utf-8') as f:
                # 对HTML文档进行编码处理，并写入文件
                html_doc = utils.EncodingHtml(url, html_doc)
                f.write(html_doc)

            # 将抓取到的页面信息插入数据库
            sql = f"INSERT INTO {args.target_table}{args.table_attrs} VALUES ('{hash_val}', '{url}', '{db_index}');"
            cursor.execute(sql)

        file_index += 1  # 文件索引递增

        # 定期打印已抓取和剩余要抓取的页面数量
        if file_index % args.PRINTFREQ == 0 or len(queue) == 0:
            print(f"> Pages crawled: {file_index} | URL in queue: {len(queue)} <")

        # 定期保存检查点数据和提交数据库事务
        if file_index % args.page_ckpt_len == 0:
            print("————————Saving: please don't abort the application.————————")
            if args.output_mode != "redis":
                conn.commit()  # 提交数据库事务

            # 保存检查点数据到文件
            with open(args.DataPath + "crawler_ckpt.pkl", "wb") as pickled:
                pickle.dump((queue, file_index), pickled)
            print("———————————————————— Data in queue saved. ————————————————————")

    # 打印爬虫结束信息
    print(f"Spider finished! Totally {file_index} documents parsed.")

    # 最后一次提交数据库事务
    print("————————Saving: please don't abort the application.————————")
    conn.commit()
    if os.path.exists(args.DataPath + "crawler_ckpt.pkl"):
        os.remove(args.DataPath + "crawler_ckpt.pkl")
    print("————————————————————    Data saved.    ————————————————————")




if __name__ == '__main__':
    '''starting html'''
    starting_page = ["https://service.ruc.edu.cn/v2/site/index"]


    '''set parser'''
    # general
    parser = argparse.ArgumentParser(description='Crawler')
    parser.add_argument('--mode', type=str, default='RESTART', choices=['TEST', 'RUNNING', 'RESTART'])
    parser.add_argument('--single_page_mode', type=bool, default=True)
    parser.add_argument('--db_size', type=str, default='{:07}')
    parser.add_argument('--target_table', type=str, default='service_page_text')
    parser.add_argument('--table_attrs', type=str, default='(page_hash, page_url, db_index)')

    # data
    parser.add_argument('--input_mode', type=str, default="excel", choices=['default', 'txt', 'excel'])
    parser.add_argument('--output_mode', type=str, default="redis", choices=['redis', 'mySQL&Local'])

    parser.add_argument('--DataPath', type=str, default="./data/")
    parser.add_argument('--HtmlPath', type=str, default="./database_service/")
    parser.add_argument('--DocPath', type=str, default="./document/")

    parser.add_argument('--DataFile', type=str, default="url.xlsx")
    parser.add_argument('--headers', type=dict, default={'user-agent': 'my-app/0.0.1'})
    parser.add_argument('--SUBPAGE_SIZE', type=int, default=10000)

    # redis
    parser.add_argument('--redis_host', type=str, default="localhost")
    parser.add_argument('--redis_port', type=int, default=6379)
    parser.add_argument('--redis_db', type=int, default=0)

    # ckpt
    parser.add_argument('--page_ckpt_len', type=int, default=10)
    parser.add_argument('--PRINTFREQ', type=int, default=10)

    # net
    parser.add_argument('--pause_time', type=float, default=0.1)
    parser.add_argument('--timeout', type=int, default=3)
    parser.add_argument('--MAX_RECONNECT_CNT', type=int, default=3)

    args = parser.parse_args()
    cursor = None

    if args.input_mode == 'txt':
        with open(args.DataPath + "url_list.txt", 'r', encoding='utf-8') as f:
            for url in f.readlines():
                starting_page.append(url.strip())

    if args.input_mode == 'excel':
        starting_page = pd.read_excel(args.DataPath + args.DataFile)["link"].tolist()

    '''connect to MySQL'''
    if not args.single_page_mode:
        conn = pymysql.connect(
            host=       "Localhost",
            database=   "hqjt",
            user=       "root",
            password=   "Zwzs030624"
        )
        cursor = conn.cursor()

    if args.mode == 'RESTART':
        if os.path.exists(args.HtmlPath):
            shutil.rmtree(args.HtmlPath)
        if os.path.exists(args.DataPath + "crawler_ckpt.pkl"):
            os.remove(args.DataPath + "crawler_ckpt.pkl")

        if not args.single_page_mode:
            sql = f"TRUNCATE TABLE {args.target_table};"
            cursor.execute(sql)
            conn.commit()

    '''main()'''
    crawler(starting_page ,args, cursor)

    conn.close()
