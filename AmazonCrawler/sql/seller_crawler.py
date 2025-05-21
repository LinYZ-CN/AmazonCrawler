import pymysql
from datetime import datetime, timedelta
from typing import List, Optional
from AmazonCrawler.sql.db_config import DB_CONFIG


class AmazonSellerCrawlerDB:
    """
    Amazon 爬虫数据库管理类
    功能：
    1. 管理 sellers/products/seller_products 三张表
    2. 获取需要爬取的 seller_id 和 asin（7天未更新的数据）
    3. 自动标记已爬取状态
    4. 支持事务处理和错误回滚
    """

    def __init__(self):
        """初始化数据库连接并确保表存在"""
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            self._create_tables()
        except pymysql.Error as e:
            raise ConnectionError(f"数据库连接失败: {e}")

    def _create_tables(self) -> None:
        """创建数据库表"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_sellers (
                    seller_id       VARCHAR(50),
                    region          VARCHAR(20),
                    last_crawled_at DATETIME NULL,
                    need_crawl      BOOLEAN DEFAULT TRUE,
                    PRIMARY KEY (seller_id, region),
                    INDEX idx_crawl_status (need_crawl, last_crawled_at),
                    INDEX idx_region (region)
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS crawl_products (
                    asin            VARCHAR(20),
                    region          VARCHAR(20),
                    last_crawled_at DATETIME NULL,
                    need_crawl      BOOLEAN DEFAULT TRUE,
                    PRIMARY KEY (asin, region),
                    INDEX idx_crawl_status (need_crawl, last_crawled_at),
                    INDEX idx_region (region)
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS seller_products (
                    id         INT AUTO_INCREMENT PRIMARY KEY,
                    seller_id  VARCHAR(50),
                    asin       VARCHAR(20),
                    region     VARCHAR(20),
                    delivery   VARCHAR(255),
                    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (seller_id, region) REFERENCES crawl_sellers (seller_id, region),
                    FOREIGN KEY (asin, region) REFERENCES crawl_products (asin, region),
                    UNIQUE KEY uk_relation (seller_id, asin, region),
                    INDEX idx_crawled_at (crawled_at)
                )
            ''')

            self.conn.commit()
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"创建表失败: {e}")

    def get_sellers_to_crawl(
            self,
            region,
            min_days: int = 7
    ) -> List[str]:
        """获取需要爬取的卖家ID列表"""
        try:
            self.cursor.execute('''
                SELECT seller_id
                FROM crawl_sellers
                WHERE (last_crawled_at IS NULL OR last_crawled_at < %s)
                  AND region = %s
                  AND need_crawl = TRUE
                ORDER BY last_crawled_at ASC
            ''', (datetime.now() - timedelta(days=min_days), region))
            return [row[0] for row in self.cursor.fetchall()]
        except pymysql.Error as e:
            raise RuntimeError(f"查询卖家失败: {e}")

    def get_products_to_crawl(
            self,
            region,
            min_days: int = 7
    ) -> List[str]:
        """获取需要爬取的商品ASIN列表"""
        try:
            self.cursor.execute('''
                SELECT asin
                FROM crawl_products
                WHERE (last_crawled_at IS NULL OR last_crawled_at < %s)
                  AND region = %s
                  AND need_crawl = TRUE
                ORDER BY last_crawled_at ASC
            ''', (datetime.now() - timedelta(days=min_days), region))
            return [row[0] for row in self.cursor.fetchall()]
        except pymysql.Error as e:
            raise RuntimeError(f"查询商品失败: {e}")

    def insert_seller_product(
            self,
            seller_id: str,
            asin: str,
            delivery: str,
            region: str
    ) -> bool:
        """插入卖家-商品关系，但不标记为已爬取"""
        try:
            with self.conn.cursor() as cursor:
                # 插入 crawl_sellers（只插入 seller_id / region，不更新爬取状态）
                cursor.execute('''
                               INSERT IGNORE INTO crawl_sellers (seller_id, region)
                               VALUES (%s, %s)
                               ''', (seller_id, region))

                # 插入 crawl_products（只插入 asin / region）
                cursor.execute('''
                               INSERT IGNORE INTO crawl_products (asin, region)
                               VALUES (%s, %s)
                               ''', (asin, region))

                # 插入 seller_products（会更新 delivery 和时间戳）
                cursor.execute('''
                               INSERT INTO seller_products (seller_id, asin, delivery, region)
                               VALUES (%s, %s, %s, %s)
                               ON DUPLICATE KEY UPDATE delivery = CASE
                                                                        WHEN VALUES(delivery) IS NOT NULL AND VALUES(delivery) != ''
                                                                            THEN VALUES(delivery)
                                                                        ELSE delivery
                                   END,
                                                       crawled_at = CURRENT_TIMESTAMP
                               ''', (seller_id, asin, delivery, region))

            self.conn.commit()
            return True
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"插入失败: {e}")

    def mark_as_crawled(
            self,
            seller_id: Optional[str] = None,
            asin: Optional[str] = None,
            region: Optional[str] = None,
            success: bool = True
    ) -> None:
        """标记数据为已爬取状态"""
        if region is None:
            raise ValueError("region参数不能为空")

        try:
            with self.conn.cursor() as cursor:
                if seller_id:
                    cursor.execute('''
                        UPDATE crawl_sellers
                        SET last_crawled_at = %s,
                            need_crawl = %s
                        WHERE seller_id = %s AND region = %s
                    ''', (
                        datetime.now() if success else None,
                        not success,
                        seller_id,
                        region,
                    ))

                if asin:
                    cursor.execute('''
                        UPDATE crawl_products
                        SET last_crawled_at = %s,
                            need_crawl = %s
                        WHERE asin = %s AND region = %s
                    ''', (
                        datetime.now() if success else None,
                        not success,
                        asin,
                        region
                    ))

            self.conn.commit()
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"标记失败: {e}")

    def close(self) -> None:
        """关闭数据库连接"""
        try:
            self.cursor.close()
            self.conn.close()
        except pymysql.Error as e:
            raise RuntimeError(f"关闭连接失败: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 使用示例
if __name__ == '__main__':
    with AmazonSellerCrawlerDB() as db:
        # 获取指定region待爬取卖家
        sellers = db.get_sellers_to_crawl(region='UK')
        print("待爬取的卖家:", sellers)

        # 获取指定region待爬取商品
        products = db.get_products_to_crawl(region='UK')
        print("待爬取的商品:", products)

        db.mark_as_crawled(asin='B00IEG2K2S', region='UK', success=True)
