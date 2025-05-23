# AmazonCrawler 项目文档

## 项目简介

AmazonCrawler 是一个用于抓取亚马逊商品信息的爬虫工具。支持通过关键词搜索商品，自动采集商品标题、价格、评分、评论数、商品链接等信息，并可将结果导出为 Excel 或 CSV 文件，方便后续数据分析与处理。

## 技术栈

- Python 3.x
- requests / httpx
- BeautifulSoup / lxml
- pandas
- Selenium（可选，用于处理动态加载页面）
- 其他依赖请参考 `requirements.txt`

## 安装与运行

1. **克隆项目代码**
   ```bash
   git clone https://github.com/yourname/AmazonCrawler.git
   cd AmazonCrawler
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置参数**
   - 根据需要修改 `config.py` 或 `.env` 文件，设置关键词、输出路径等参数。

4. **运行爬虫**
   ```bash
   python main.py
   ```

## 目录结构说明

```
AmazonCrawler/
├── main.py              # 项目主入口
├── crawler/             # 爬虫核心代码
│   ├── amazon_spider.py # 亚马逊爬虫实现
│   └── utils.py         # 工具函数
├── output/              # 爬取结果输出目录
├── requirements.txt     # 依赖包列表
├── config.py            # 配置文件
└── README.md            # 项目文档
```

## 主要功能模块说明

- **main.py**  
  项目主入口，负责参数解析、任务调度和流程控制。

- **crawler/amazon_spider.py**  
  实现亚马逊商品信息的抓取逻辑，包括请求发送、页面解析、数据提取等。

- **crawler/utils.py**  
  常用工具函数，如数据清洗、去重、导出等。

- **output/**  
  存放爬取到的商品数据文件。

- **config.py**  
  配置爬虫参数，如关键词、请求头、代理等。

## 常见问题

1. **被亚马逊封禁 IP？**  
   建议使用代理池，降低单个 IP 访问频率，或增加请求间隔。

2. **页面结构变化导致爬虫失效？**  
   需及时更新解析规则，适配最新页面结构。

3. **验证码/滑块验证？**  
   可尝试使用 Selenium 自动化，或手动处理验证码。
