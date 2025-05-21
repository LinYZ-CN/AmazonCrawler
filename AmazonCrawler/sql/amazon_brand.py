import pymysql
from AmazonCrawler.sql.db_config import DB_CONFIG


class AmazonBrand:
    def __init__(self):
        """初始化数据库连接并确保表存在"""
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            self._create_tables()
            self.migrate_brands_from_products()
        except pymysql.Error as e:
            raise ConnectionError(f"数据库连接失败: {e}")

    def _create_tables(self):
        """创建品牌表（如果不存在）"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS amazon_brand
                (
                    id         INT AUTO_INCREMENT PRIMARY KEY,
                    brand      VARCHAR(255),
                    region     VARCHAR(50) NOT NULL,
                    status     VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_brand_region (brand, region),  -- 品牌和地区的唯一组合
                    INDEX idx_brand (brand),  -- 品牌字段索引
                    INDEX idx_region (region)  -- 地区字段索引
                )
            ''')
            self.conn.commit()
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"创建表失败: {e}")

    def migrate_brands_from_products(self):
        """
        从产品表迁移品牌数据到品牌表
        只迁移品牌和地区信息，不迁移状态
        自动跳过已存在的品牌-地区组合
        :return: 迁移的新记录数量
        """
        try:
            self.cursor.execute('''
                INSERT IGNORE INTO amazon_brand (brand, region)
                SELECT DISTINCT brand, region 
                FROM amazon_products 
                WHERE brand IS NOT NULL AND brand != ''  -- 排除空品牌
            ''')
            migrated_count = self.cursor.rowcount  # 获取迁移的记录数
            self.conn.commit()
            return migrated_count
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"品牌数据迁移失败: {e}")

    def get_brands_by_region(self, region):
        """
        根据地区获取品牌列表
        条件：状态为空 或 (状态为0 且 更新时间大于7天)

        :param region: 国家/地区代码
        :return: 该地区下符合条件的品牌列表
        """
        try:
            self.cursor.execute('''
                                SELECT brand
                                FROM amazon_brand
                                WHERE region = %s
                                  AND (
                                    status IS NULL
                                        OR (status = 0 AND updated_at < DATE_SUB(NOW(), INTERVAL 7 DAY))
                                    )
                                ''', (region,))
            return [row[0] for row in self.cursor.fetchall()]  # 提取品牌名称列表
        except pymysql.Error as e:
            raise RuntimeError(f"获取地区品牌列表失败: {e}")

    def update_brand_status(self, brand, region, status):
        """
        更新指定品牌在指定地区的状态
        :param brand: 品牌名称
        :param region: 国家/地区代码
        :param status: 要设置的状态
        :return: 受影响的行数
        """
        try:
            self.cursor.execute('''
                UPDATE amazon_brand 
                SET status = %s 
                WHERE brand = %s AND region = %s
            ''', (status, brand, region))
            affected_rows = self.cursor.rowcount  # 获取受影响的行数
            self.conn.commit()
            return affected_rows
        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"更新品牌状态失败: {e}")

    def __del__(self):
        """析构函数，自动关闭数据库连接"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

if __name__ == '__main__':
    spider = AmazonBrand()
    print(spider.get_brands_by_region(region='JP'))