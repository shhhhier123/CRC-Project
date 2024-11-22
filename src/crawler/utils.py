from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import re

# class posting with tf value
class posting(object):
    special_doc_id = -1

    def __init__(self, doc_id, tf=0.0):
        self.doc_id = doc_id
        self.tf = float(tf)

    def __repr__(self):
        return "%d,%.6f" % (self.doc_id, self.tf)


def file2list(file_path, encoding_mode='utf-8'):
    res = []
    with open(file_path, 'r', encoding=encoding_mode) as f:
        for line in f:
            line = line.strip()
            if len(line) > 0:
                res.append(line)
    return res


def EncodingHtml(url, doc):
    doc = url + "\n" + doc
    return doc


def DecodingHtml(doc):
    url, doc = doc.split("\n", 1)
    return url, doc


def checkio(url):
    """
    对给定的URL字符串进行规范化处理。

    Args:
        url: 要处理的URL字符串。

    Returns:
        规范化处理后的URL字符串。
    """
    # 将URL转换为小写，并将':8080'替换为':08080'
    url = url.lower().replace(':8080', ':08080')

    # 替换URL中的特定百分比编码为对应字符
    url = (url.replace('%2d', '-').replace('%2e', '.').replace('%5f', '_')
           .replace('%7e', '~').replace(':80','').replace(':08080', ':8080'))

    # 分割URL字符串，以'%'为分隔符
    data = url.split('%')

    for i in range(len(data)):
        try:
            # 尝试将'%'后的两位字符转换为十六进制整数
            char = int(data[i][:2], 16)
            # 如果转换后的字符是字母或数字，则将其转换为小写字符并拼接剩余部分
            # 否则，如果当前片段不是第一个片段，则将'%'后的两位字符转换为大写并拼接剩余部分
            if (65 <= char <= 91) or (97 <= char <= 122) or (48 <= char <= 57):
                data[i] = chr(char).lower() + data[i][2:]
            else:
                if i > 0:
                    data[i] = '%' + data[i][:2].upper() + data[i][2:]

        except:
            # 如果转换失败，且当前片段不是第一个片段，则将'%'后的两位字符转换为大写并拼接剩余部分
            if i > 0:
                data[i] = '%' + data[i][:2].upper() + data[i][2:]
                # 将处理后的片段重新拼接为完整的URL字符串
    url = ''.join(data)

    # 初始化结果列表和索引
    ret = []
    i = 0

    # 遍历处理后的URL字符串，进行路径规范化处理
    while i < len(url):
        # 如果遇到'/..'，则删除结果列表中的最后一个非'/'字符（模拟返回上一级目录）
        if i + 2 < len(url) and url[i:i + 3] == '/..':
            while ret.pop(-1) != '/':
                pass
            i += 3
            # 如果遇到'/.'，则跳过当前片段
        elif i + 1 < len(url) and url[i:i + 2] == '/.':
            i += 2
        else:
            # 否则，将当前字符添加到结果列表中
            ret.append(url[i])
            i += 1

    # 将结果列表重新拼接为字符串，得到规范化处理后的URL
    url = ''.join(ret)
    return url


def selenium_crawling(url):
    option = webdriver.ChromeOptions()
    option.add_argument("headless")
    browser = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=option)
    browser.get(url)
    page = browser.page_source

    browser.close()
    return page


def extract_main_text_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    # 获取所有文本内容，包括标签内的文本
    text = soup.get_text()
    # 使用正则表达式提取中文、英文、标点符号和数字
    # [\u4e00-\u9fff] 是中文范围
    # [a-zA-Z] 是英文大小写字母
    # [\p{P}] 是标点符号
    # \d 是数字
    mixed_content_pattern = re.compile(r'[\u4e00-\u9fffa-zA-Z\d\s，。！？；：、\'\"（）\[\]\{\}《》\-—]+')
    mixed_content = mixed_content_pattern.findall(text)
    # 将提取的混合内容拼接成字符串，并去除多余的空格
    result = '\n'.join(mixed_content).strip()
    result = re.sub(r'\s*\n+\s*', '\n', result)
    result = re.sub(r'\n+', '\n', result)
    return result


if __name__ == '__main__':
    content = selenium_crawling('http://www.baidu.com')
    content = extract_main_text_from_html(content)
    print(content)
