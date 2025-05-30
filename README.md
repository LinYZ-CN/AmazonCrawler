# AmazonCrawler 项目说明

## 项目简介

AmazonCrawler 是一个基于 Scrapy + PyQt5 的亚马逊商品与商标信息采集系统，支持美国、英国、日本、德国等站点的商品、卖家、品牌、商标等多维度数据自动化采集、存储与导出。项目包含爬虫、数据库管理、数据导出和可视化界面，适用于电商数据分析、品牌监控等场景。

---

## 主要功能

- **多站点支持**：支持亚马逊 US/UK/JP/DE 站点。
- **商品采集**：采集畅销榜、指定 ASIN、卖家商品等信息。
- **卖家采集**：采集卖家信息、卖家商品关系。
- **品牌/商标采集**：自动查询日本、欧盟、美国商标状态。
- **数据存储**：所有数据自动写入 MySQL 数据库，结构化管理。
- **数据导出**：支持按日期、国家筛选导出 CSV。
- **可视化界面**：PyQt5 UI 支持流程选择、参数输入、日志查看、数据导出等。

---

## 目录结构

```
AmazonCrawler/
├── AmazonCrawler/
│   ├── items.py           # Scrapy Item 定义
│   ├── middlewares.py     # Scrapy 中间件（含国家 cookies 切换）
│   ├── pipelines.py       # 数据入库逻辑
│   ├── settings.py        # Scrapy 配置
│   ├── spiders/           # 各类爬虫
│   │   ├── best_seller.py
│   │   ├── jpo_brand.py
│   │   ├── product_info.py
│   │   ├── seller_asin.py
│   │   ├── seller_shop.py
│   │   ├── tm_brand.py
│   │   └── uspto_spider.py
│   └── sql/               # 数据库操作模块
│       ├── amazon_brand.py
│       ├── amazon_product.py
│       ├── db_config.py
│       ├── seller_crawler.py
│       └── uspto_brand.py
├── run_crawler_ui.py      # 图形化界面入口
├── requirements.txt       # 依赖包列表
├── scrapy.cfg             # Scrapy 配置
├── processed_files.json   # 已处理 USPTO 文件记录
└── .idea/                 # IDE 配置
```

---

## 环境依赖

- Python 3.8+
- MySQL 5.7/8.0
- 推荐使用虚拟环境

安装依赖：

```sh
pip install -r requirements.txt
```

---

## 数据库配置

请在 `AmazonCrawler/sql/db_config.py` 中配置你的 MySQL 连接信息：

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '你的密码',
    'db': 'amazon',
    'charset': 'utf8mb4',
    "init_command": "SET time_zone = '+8:00'"
}
```

首次运行会自动建表。

---

## 使用方法

### 1. 启动图形界面

```sh
python run_crawler_ui.py
```

- 选择采集流程（如畅销榜、卖家采集、商标查询等）
- 输入参数（如 ASIN、URL、品牌等）
- 查看日志、导出数据

### 2. 命令行运行爬虫

如采集畅销榜：

```sh
scrapy crawl best_seller -a url="https://www.amazon.com/Best-Sellers/zgbs"
```

采集卖家商品：

```sh
scrapy crawl seller_shop -a region=US -a asin_all="B08XXXXXX B09YYYYYY"
```

采集商标：

```sh
scrapy crawl jpo_brand -a region=JP
scrapy crawl tm_brand -a region=DE
```

采集 USPTO 商标数据：

```sh
scrapy crawl uspto_spider
```

---

## 数据导出

在 UI 界面点击“导出数据”，可按日期范围、国家筛选导出 CSV 文件。

---

## 主要模块说明

- `AmazonCrawler/items.py`：定义所有爬取数据结构。
- `AmazonCrawler/pipelines.py`：负责数据入库。
- `AmazonCrawler/sql/`：所有数据库表结构和操作。
- `AmazonCrawler/spiders/`：各类采集爬虫。
- `run_crawler_ui.py`：PyQt5 图形界面主程序。

---

## 常见问题

- **数据库连接失败**：请检查 MySQL 是否启动、配置是否正确。
- **采集不到数据**：部分站点有反爬机制，建议适当调整请求频率或更换 IP。
- **界面乱码**：请确保系统字体支持中文，或调整 PyQt5 字体设置。

---

## 贡献与反馈

如有建议、Bug 或需求，欢迎提交 Issue 或 PR。

---

## License

本项目仅供学习与研究使用，禁止用于商业用途。