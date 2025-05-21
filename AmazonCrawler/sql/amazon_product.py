import pymysql
from AmazonCrawler.sql.db_config import DB_CONFIG


class AmazonProduct:
    def __init__(self):
        """初始化数据库连接并确保表存在"""
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            self._create_tables()
            self.update_product_status_from_brand()
        except pymysql.Error as e:
            raise ConnectionError(f"数据库连接失败: {e}")

    def _create_tables(self):
        """创建产品表"""
        try:
            self.cursor.execute('''
                                CREATE TABLE IF NOT EXISTS amazon_products
                                (
                                    id         INT AUTO_INCREMENT PRIMARY KEY,
                                    asin       VARCHAR(10) NOT NULL,
                                    brand      VARCHAR(255),
                                    price      DECIMAL(10, 2),
                                    sale       INT,
                                    region     VARCHAR(50) NOT NULL,
                                    status     VARCHAR(10),
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                    UNIQUE KEY uk_asin_region (asin, region),
                                    INDEX idx_asin (asin),
                                    INDEX idx_brand (brand),
                                    INDEX idx_region (region)
                                )
                                ''')
            self.conn.commit()
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"创建表失败: {e}")

    def update_product_status_from_brand(self):
        """
        根据 amazon_brand 表中的品牌状态更新 amazon_products 表中的产品状态
        """
        try:
            # 更新有匹配品牌记录的产品状态
            self.cursor.execute('''
                                UPDATE amazon_products p
                                    JOIN amazon_brand b ON p.brand = b.brand AND p.region = b.region
                                SET p.status = b.status
                                WHERE p.status IS NULL
                                   OR p.status != b.status
                                ''')
            updated_rows = self.cursor.rowcount
            self.conn.commit()
            return updated_rows
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"更新产品状态失败: {e}")

    def insert_product(self, asin: str, region: str, brand: str = None,
                       price: float = None, sale: int = None, status: str = None):
        """
        插入或更新产品数据到数据库

        参数:
            asin: 产品ASIN (必须)
            region: 地区 (必须)
            brand: 品牌 (可选)
            price: 价格 (可选)
            sale: 销量 (可选)
            status: 状态，默认为'' (可选)
        """
        if not asin or not region:
            raise ValueError("asin和region是必填参数")

        sql = """
              INSERT INTO amazon_products (asin, brand, price, sale, region, status)
              VALUES (%s, %s, %s, %s, %s, %s)
              ON DUPLICATE KEY UPDATE brand      = VALUES(brand), \
                                      price      = VALUES(price), \
                                      sale       = VALUES(sale), \
                                      status     = VALUES(status), \
                                      updated_at = CURRENT_TIMESTAMP \
              """

        try:
            self.cursor.execute(sql, (asin, brand, price, sale, region, status))
            self.conn.commit()
            return True
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"插入产品数据失败: {e}")
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"发生意外错误: {e}")

    def migrate_seller_products(self):
        """
        从 seller_products 表迁移 asin 和 region 数据到 amazon_products 表
        只迁移不重复的数据
        """
        try:
            # 查询 seller_products 表中所有唯一的 asin 和 region 组合
            self.cursor.execute('''
                                SELECT DISTINCT sp.asin, sp.region
                                FROM seller_products sp
                                         LEFT JOIN amazon_products ap ON sp.asin = ap.asin AND sp.region = ap.region
                                WHERE ap.asin IS NULL
                                ''')

            rows = self.cursor.fetchall()
            if not rows:
                print("没有需要迁移的新数据")
                return 0

            # 批量插入新数据
            insert_sql = '''
                         INSERT INTO amazon_products (asin, region)
                         VALUES (%s, %s)
                         ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP \
                         '''

            self.cursor.executemany(insert_sql, rows)
            self.conn.commit()

            print(f"成功迁移 {self.cursor.rowcount} 条数据")
            return self.cursor.rowcount

        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"数据迁移失败: {e}")
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"发生意外错误: {e}")

    def get_asin_by_region(self, region):
        """
        查询 brand 为空的记录，返回 asin 列表（不包含 region）

        参数:
            region (str): 要筛选的 region 值

        返回:
            List[str]: 仅包含 asin 的列表，例如 ["B00123", "B00456"]
        """
        try:
            self.cursor.execute('''
                                SELECT asin
                                FROM amazon_products
                                WHERE (brand IS NULL OR brand = '')
                                  AND region = %s
                                ''', (region,))
            return [row[0] for row in self.cursor.fetchall()]
        except pymysql.Error as e:
            raise RuntimeError(f"查询失败: {e}")


    def __del__(self):
        """析构函数，关闭数据库连接"""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    # 初始化
    product_db = AmazonProduct()
    product_db.update_product_status_from_brand()
    # try:
    #     migrated_count = product_db.migrate_seller_products()
    #     print(f"共迁移了 {migrated_count} 条新记录")
    # except Exception as e:
    #     print(f"迁移过程中出错: {e}")
    # print(product_db.get_brands_with_empty_status(region="JP"))
    # print(product_db.get_asin())