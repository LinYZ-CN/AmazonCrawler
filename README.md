# AmazonCrawler 项目说明

## 项目简介

AmazonCrawler 是一个基于 Scrapy + PyQt5 的亚马逊商品与商标信息采集系统，支持美国、英国、日本、德国等站点的商品、卖家、品牌、商标等多维度数据自动化采集、存储与导出。项目包含爬虫、数据库管理、数据导出和可视化界面，适用于电商数据分析、品牌监控等场景。

本项目通过友好的图形界面，让用户无需编程知识即可轻松采集亚马逊平台数据，同时提供命令行接口满足高级用户的自动化需求。

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

### 安装步骤

1. 克隆或下载项目代码
2. 创建并激活虚拟环境（可选但推荐）
   ```sh
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. 安装依赖包
   ```sh
   pip install -r requirements.txt
   ```
4. 配置数据库（见下一节）

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

### 核心模块

- `AmazonCrawler/items.py`：定义所有爬取数据结构。
- `AmazonCrawler/pipelines.py`：负责数据入库。
- `AmazonCrawler/middlewares.py`：处理请求和响应的中间件，包含国家/地区切换逻辑。
- `AmazonCrawler/settings.py`：Scrapy 配置参数。
- `run_crawler_ui.py`：PyQt5 图形界面主程序。

### 数据库模块

- `AmazonCrawler/sql/db_config.py`：数据库连接配置。
- `AmazonCrawler/sql/amazon_product.py`：商品数据表操作。
- `AmazonCrawler/sql/amazon_brand.py`：品牌数据表操作。
- `AmazonCrawler/sql/seller_crawler.py`：卖家数据表操作。
- `AmazonCrawler/sql/uspto_brand.py`：美国商标数据表操作。

### 爬虫模块

- `AmazonCrawler/spiders/best_seller.py`：亚马逊畅销榜爬虫，支持多站点、自动翻页。
- `AmazonCrawler/spiders/product_info.py`：商品详情爬虫，提取价格、评分、库存等信息。
- `AmazonCrawler/spiders/seller_shop.py`：卖家店铺爬虫，采集卖家基本信息。
- `AmazonCrawler/spiders/seller_asin.py`：卖家商品爬虫，采集卖家所有在售商品。
- `AmazonCrawler/spiders/jpo_brand.py`：日本商标查询爬虫，查询品牌在日本的商标状态。
- `AmazonCrawler/spiders/tm_brand.py`：欧盟商标查询爬虫，查询品牌在欧盟的商标状态。
- `AmazonCrawler/spiders/uspto_spider.py`：美国商标查询爬虫，查询品牌在美国的商标状态。

---

## 技术架构

本项目采用分层架构设计，主要分为以下几层：

1. **界面层**：基于 PyQt5 构建的图形用户界面，提供流程选择、参数输入和结果展示。
2. **爬虫层**：基于 Scrapy 框架的多个爬虫，负责数据采集和解析。
3. **数据层**：MySQL 数据库存储和管理采集的数据。
4. **业务逻辑层**：连接界面和数据层，处理数据流转和业务规则。

### 数据流向

```
用户输入 → PyQt5界面 → Scrapy爬虫 → 数据解析 → MySQL数据库 → 数据导出/展示
```

### 并发与性能

- 使用 Scrapy 的异步请求机制提高采集效率
- 针对不同站点和爬虫类型，自动调整并发请求数
- 实现请求重试和错误处理机制，提高稳定性

---

## 常见问题

- **数据库连接失败**：请检查 MySQL 是否启动、配置是否正确。
- **采集不到数据**：部分站点有反爬机制，建议适当调整请求频率或更换 IP。
- **界面乱码**：请确保系统字体支持中文，或调整 PyQt5 字体设置。
- **爬虫运行缓慢**：可能是网络问题或目标站点限流，尝试在 settings.py 中调整 DOWNLOAD_DELAY。
- **数据不完整**：某些字段可能因页面结构变化而无法提取，请检查并更新相应的 XPath 选择器。
- **内存占用过高**：处理大量数据时可能发生，建议增加分批处理或调整 CONCURRENT_REQUESTS 参数。

---

## 未来计划

项目计划在未来版本中添加以下功能：

- 支持更多亚马逊国际站点（如加拿大、澳大利亚等）
- 增加商品评论采集功能
- 添加数据可视化分析模块
- 实现自动化定时采集任务
- 优化反爬策略，提高稳定性
- 增加更多商标数据源

---

## 贡献与反馈

如有建议、Bug 或需求，欢迎提交 Issue 或 PR。项目持续更新中，欢迎参与贡献！

### 如何贡献

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## License

本项目仅供学习与研究使用，禁止用于商业用途。

---

## 致谢

感谢所有为本项目做出贡献的开发者！
