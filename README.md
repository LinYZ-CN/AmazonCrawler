# AmazonCrawler

## 项目简介

AmazonCrawler 是一个支持多站点（美国、英国、德国、日本）亚马逊数据采集的爬虫系统，具备畅销榜、卖家、品牌、商标等多维度采集能力。项目支持命令行与图形界面（GUI）双模式运行，适合数据分析、市场调研等多种应用场景。

## 主要功能

- 支持采集亚马逊畅销榜商品、卖家商品、品牌信息、商标数据等
- 支持多国家/地区（US、UK、JP、DE）
- 自动识别URL所属国家，支持自动翻页
- 数据可导出，支持自定义采集参数
- 提供 PySide6 实现的现代化 GUI 操作界面

## 环境依赖

请确保已安装 Python 3.8 及以上版本。依赖包详见 `requirements.txt`，主要包括：

- Scrapy
- PySide6
- PyMySQL
- lxml
- requests
- 及其他爬虫、数据库、GUI相关依赖

安装依赖命令：

```bash
pip install -r requirements.txt
```

## 数据库配置

本项目默认使用 MySQL 数据库存储采集结果。请在 `AmazonCrawler/sql/db_config.py` 中配置数据库连接参数：

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'db': 'amazon',
    'charset': 'utf8mb4',
    "init_command": "SET time_zone = '+8:00'"
}
```
请确保数据库已创建，并有相应权限。

## 启动方式

### 1. 图形界面（推荐）

直接运行根目录下的 `run_crawler_ui.py`：

```bash
python run_crawler_ui.py
```

首次运行会自动弹出 GUI 界面，支持选择爬虫类型、国家、参数输入、日志查看与数据导出等操作。

### 2. 命令行模式

进入项目根目录，使用 Scrapy 命令行运行各类爬虫。例如：

- **畅销榜采集**  
  ```bash
  scrapy crawl best_seller -a url="https://www.amazon.com/s?rh=n%3A12896671&fs=true"
  ```
  - `url` 参数为畅销榜页面地址，支持 amazon.com/.co.uk/.de/.co.jp

- **品牌产品采集**  
  ```bash
  scrapy crawl product_info -a region=US
  ```
  - `region` 参数为国家代码（US/UK/JP/DE）

- **卖家商品采集**  
  ```bash
  scrapy crawl seller_asin -a region=US -a seller_all="A2HSJEX0PJ2MFY"
  ```
  - `seller_all` 可为单个或多个卖家ID

- **商标数据采集**  
  ```bash
  scrapy crawl uspto_spider
  ```

更多参数和用法请参考 `AmazonCrawler/spiders/` 目录下各爬虫脚本的注释说明。

## 目录结构

```
AmazonCrawler/
├── AmazonCrawler/
│   ├── items.py
│   ├── middlewares.py
│   ├── pipelines.py
│   ├── settings.py
│   ├── spiders/
│   │   ├── best_seller.py
│   │   ├── product_info.py
│   │   ├── seller_asin.py
│   │   ├── seller_shop.py
│   │   ├── jpo_brand.py
│   │   ├── tm_brand.py
│   │   └── uspto_spider.py
│   └── sql/
│       ├── amazon_brand.py
│       ├── amazon_product.py
│       ├── db_config.py
│       ├── seller_crawler.py
│       └── uspto_brand.py
├── requirements.txt
├── run_crawler_ui.py
└── scrapy.cfg
```

## 常见问题

- **GUI无法启动/报错**：请确认已正确安装 PySide6 及相关依赖，且 Python 版本符合要求。
- **数据库连接失败**：请检查 `db_config.py` 配置及数据库服务状态。
- **采集无数据**：请确认参数填写正确，目标页面可正常访问，且未被反爬虫机制限制(触发反扒机制需要修改中间件（middlewares）中的cookies或者更换ip)。


## 联系与支持

如有问题或建议，欢迎提交 issue 或联系开发者。 