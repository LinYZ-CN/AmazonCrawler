import os
import json
import zipfile
from io import BytesIO
from datetime import datetime

import scrapy
from lxml import etree
from AmazonCrawler.items import UsptoItem


class UsptoSpider(scrapy.Spider):
    """
    USPTO 商标数据爬虫：
    从 https://data.uspto.gov 下载并解析 XML ZIP 文件，
    抽取商标注册信息并生成 UsptoItem 实例。
    """
    name = 'uspto_spider'
    allowed_domains = ['data.uspto.gov']


    base_url = 'https://data.uspto.gov/ui/datasets/products/trtdxfap'
    today = datetime.today().strftime('%Y-%m-%d')  # 当前日期，用于筛选文件
    # 站点访问时附带的 cookies（如有 WAF 验证，可在此处设置）

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_count = 0  # 初始化计数器

        self.processed_files_path = 'processed_files.json'
        self.processed_files = self.load_processed_files()

        self.cookies = {
            '_ga_6K78XHX69P': 'GS1.1.1744185850.1.0.1744185850.0.0.0',
            '_ga': 'GA1.1.1135695563.1744185851',
            '_ga_CD30TTEK1F': 'GS1.1.1744185854.1.0.1744185856.0.0.0',
            'x-hng': 'lang=zh-CN&domain=data.uspto.gov',
            '_ga_ZRGD3GSPSL': 'GS1.1.1744451290.3.1.1744451709.0.0.0',
            '_ga_1KBHG37G8W': 'GS1.1.1744774118.2.1.1744775400.0.0.0',
            '_ga_CSLL4ZEK4L': 'GS1.1.1744774118.6.1.1744775400.0.0.0',
        }

    def start_requests(self):
        """
        初始请求入口：
        - 创建保存目录（如需要）
        - 加载已处理文件列表
        - 构造接口 URL，发起获取文件列表的请求
        """
        self.processed_path = os.path.join(os.getcwd(), 'processed_files.json')

        params = {
            'includeFiles': 'true',
            'fileDataFromDate': '2025-01-01',
            'fileDataToDate': self.today
        }
        url = f"{self.base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

        yield scrapy.Request(url, callback=self.parse_file_list)

    def load_processed_files(self):
        """
        加载已处理文件列表（防止重复抓取）：
        如果文件存在，解析 JSON 内容，否则返回空列表。
        """
        if os.path.exists(self.processed_files_path):
            with open(self.processed_files_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save_processed_files(self):
        """
        保存已处理文件名列表到 JSON 文件中。
        """
        with open(self.processed_files_path, 'w') as f:
            json.dump(self.processed_files, f, ensure_ascii=False, indent=4)

    def parse_file_list(self, response):
        """
        解析 JSON 文件列表接口响应：
        - 获取每个 ZIP 文件的下载链接
        - 如果未处理，则发起下载请求
        """
        data = json.loads(response.text)
        file_bag = data['bulkDataProductBag'][0]['productFileBag']['fileDataBag']

        for file_info in file_bag:
            file_name = file_info['fileName']
            if file_name in self.processed_files:
                self.logger.info(f"跳过已处理文件: {file_name}")
                continue
            file_url = file_info['fileDownloadURI']
            yield scrapy.Request(
                url=file_url,
                cookies=self.cookies,
                callback=self.parse_zip,
                meta={'file_name': file_name},
                dont_filter=True
            )

    def parse_zip(self, response):
        """
        处理下载后的 ZIP 文件：
        - 解压文件
        - 逐个 XML 文件解析
        - 提取出每个 case-file 标签的字段，生成 UsptoItem
        - 标记该文件为已处理
        """
        file_name = response.meta['file_name']
        zf = zipfile.ZipFile(BytesIO(response.body))

        total = 0
        for name in zf.namelist():
            self.logger.info(f"解析文件: {name}")
            with zf.open(name) as xml_file:
                xml_content = xml_file.read()
                parser = etree.XMLParser(recover=True)
                root = etree.fromstring(xml_content, parser=parser)

                for elem in root.iter('case-file'):
                    item = UsptoItem()
                    item['serial_number'] = self.get_text(elem, './/serial-number')
                    item['registration_number'] = self.get_text(elem, './/registration-number')
                    item['transaction_date'] = self.parse_date(self.get_text(elem, './/transaction-date'))
                    item['filing_date'] = self.parse_date(self.get_text(elem, './/case-file-header//filing-date'))
                    item['registration_date'] = self.parse_date(self.get_text(elem, './/case-file-header//registration-date'))
                    item['status_code'] = self.get_text(elem, './/case-file-header//status-code')
                    item['status_date'] = self.parse_date(self.get_text(elem, './/case-file-header//status-date'))
                    item['mark_identification'] = self.get_text(elem, './/case-file-header//mark-identification')
                    item['attorney_name'] = self.get_text(elem, './/case-file-header//attorney-name')
                    item['case_file_owner_name'] = self.get_text(elem, './/case-file-owners//case-file-owner//party-name')
                    total += 1
                    self.total_count += 1
                    yield item
                    elem.clear()

        if total > 0:
            self.processed_files.append(file_name)
            self.save_processed_files()

    def get_text(self, elem, xpath):
        """
        提取 XPath 所指定的标签文本内容，自动去除空格。
        :param elem: 当前 XML 元素
        :param xpath: XPath 路径
        :return: 提取的文本（如有），否则 None
        """
        found = elem.find(xpath)
        return found.text.strip() if found is not None and found.text else None

    def parse_date(self, text):
        """
        将文本形式的日期（格式为 YYYYMMDD）解析为 datetime.date 类型。
        :param text: 日期字符串
        :return: 解析后的日期对象或 None
        """
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y%m%d").date()
        except:
            return None

    def closed(self, reason):
        """
        Scrapy 爬虫结束时调用，输出总抓取数据量。
        :param reason: 关闭原因
        """
        self.logger.info(f"爬虫结束，总共抓取数据条数: {self.total_count}")
