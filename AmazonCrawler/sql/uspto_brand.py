from datetime import datetime
import pymysql

from AmazonCrawler.sql.amazon_brand import AmazonBrand
from AmazonCrawler.sql.db_config import DB_CONFIG


class UsptoBrand:
    """用于处理USPTO商标数据存储和检索的类

    该类提供创建数据库表、插入/更新商标记录和查询商标状态的方法

    属性:
        conn: MySQL数据库连接对象
        cursor: 用于执行SQL查询的数据库游标
    """

    def __init__(self):
        """初始化数据库连接并确保所需表存在

        异常:
            ConnectionError: 如果数据库连接失败
        """
        try:
            self.conn = pymysql.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            self._create_tables()
            self.update_amazon_brand()
        except pymysql.Error as e:
            raise ConnectionError(f"数据库连接失败: {e}")

    def _create_tables(self):
        """创建存储USPTO商标数据所需的数据库表

        创建主表'uspto_brand'和相应的索引(如果不存在)

        异常:
            RuntimeError: 如果表创建失败
        """
        try:
            # 创建主表
            self.cursor.execute('''
                                CREATE TABLE IF NOT EXISTS uspto_brand
                                (
                                    id                   INT AUTO_INCREMENT PRIMARY KEY,
                                    serial_number        VARCHAR(100) NOT NULL COMMENT '序列号',
                                    registration_number  VARCHAR(100) NULL COMMENT '注册号',
                                    transaction_date     DATE         NULL COMMENT '交易日期',
                                    filing_date          DATE         NULL COMMENT '申请日期',
                                    registration_date    DATE         NULL COMMENT '注册日期',
                                    status_code          VARCHAR(50)  NULL COMMENT '状态代码',
                                    status_date          DATE         NOT NULL COMMENT '状态日期',
                                    mark_identification  TEXT         NULL COMMENT '商标标识',
                                    attorney_name        TEXT         NULL COMMENT '律师姓名',
                                    case_file_owner_name TEXT         NULL COMMENT '案件所有人姓名',
                                    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
                                ) ENGINE = InnoDB
                                  DEFAULT CHARSET = utf8mb4
                                  COLLATE = utf8mb4_unicode_ci COMMENT ='USPTO商标数据表';
                                ''')

            # 创建索引（分开执行以避免语法错误）
            index_queries = [
                "CREATE INDEX idx_serial_number ON uspto_brand (serial_number)",
                "CREATE INDEX idx_registration_number ON uspto_brand (registration_number)",
                "CREATE INDEX idx_status_date ON uspto_brand (status_date)",
                "CREATE INDEX idx_filing_date ON uspto_brand (filing_date)",
                "CREATE INDEX idx_mark_identification ON uspto_brand (mark_identification(255))"
            ]

            for query in index_queries:
                try:
                    self.cursor.execute(query)
                except pymysql.Error as e:
                    if "Duplicate key name" not in str(e):
                        raise

            self.conn.commit()

        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"创建表失败: {e}")

    def insert_or_update_brand(self, brand_data: dict):
        """插入或更新商标数据到数据库

        该方法遵循以下规则:
        1. 如果serial_number不存在，插入新记录
        2. 如果记录已存在但新数据的status_date更近，则更新记录
        3. 否则，不做任何操作

        参数:
            brand_data: 包含商标数据的字典，应有以下键:
                - serial_number: 商标序列号(必需)
                - registration_number: 注册号
                - transaction_date: 交易日期
                - filing_date: 申请日期
                - registration_date: 注册日期
                - status_code: 状态代码
                - status_date: 状态日期(必需)
                - mark_identification: 商标标识文本
                - attorney_name: 律师姓名
                - case_file_owner_name: 案件所有人姓名

        异常:
            RuntimeError: 如果数据库操作失败
        """
        try:
            # 首先检查是否存在该serial_number的记录
            self.cursor.execute('''
                                SELECT status_date
                                FROM uspto_brand
                                WHERE serial_number = %s
                                ORDER BY status_date DESC
                                LIMIT 1
                                ''', (brand_data.get("serial_number"),))

            existing_record = self.cursor.fetchone()

            # 准备要插入/更新的数据
            values = (
                brand_data.get("serial_number"),
                brand_data.get("registration_number"),
                brand_data.get("transaction_date"),
                brand_data.get("filing_date"),
                brand_data.get("registration_date"),
                brand_data.get("status_code"),
                brand_data.get("status_date"),
                brand_data.get("mark_identification"),
                brand_data.get("attorney_name"),
                brand_data.get("case_file_owner_name")
            )

            if not existing_record:
                # 不存在记录，直接插入
                self.cursor.execute('''
                                    INSERT INTO uspto_brand (serial_number, registration_number, transaction_date,
                                                             filing_date, registration_date, status_code,
                                                             status_date, mark_identification, attorney_name,
                                                             case_file_owner_name)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ''', values)
            else:
                # 比较日期，只更新更新的数据
                existing_date = existing_record[0]
                new_date = brand_data.get("status_date")
                new_date = datetime.strptime(new_date, "%Y-%m-%d").date() if new_date else None
                if new_date and (existing_date is None or new_date > existing_date):
                    self.cursor.execute('''
                                        UPDATE uspto_brand
                                        SET registration_number  = %s,
                                            transaction_date     = %s,
                                            filing_date          = %s,
                                            registration_date    = %s,
                                            status_code          = %s,
                                            status_date          = %s,
                                            mark_identification  = %s,
                                            attorney_name        = %s,
                                            case_file_owner_name = %s
                                        WHERE serial_number = %s
                                        ''', values[1:] + (values[0],))  # 注意最后加上serial_number作为WHERE条件

            self.conn.commit()

        except pymysql.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"品牌数据操作失败: {e}")

    def search_mark_identification(self, keyword: str) -> str:
        """根据商标标识文本搜索商标状态

        搜索过程分为三步以避免表连接，并实现了状态代码的优先级系统:
        1. 最高优先级: "Registered" 或 "Live"
        2. 中等优先级: "Pending"
        3. 最低优先级: "Dead" 或 "Indifferent"

        参数:
            keyword: 在mark_identification字段中查找的搜索词

        返回:
            str: 找到的最高优先级状态，如果没有匹配优先级则返回第一个状态

        异常:
            RuntimeError: 如果数据库查询失败
        """
        try:
            # 第一步：从大表获取所有匹配的status_code
            self.cursor.execute('''
                                SELECT DISTINCT status_code
                                FROM uspto_brand
                                WHERE mark_identification LIKE %s
                                ''', keyword)

            status_codes = [row[0] for row in self.cursor.fetchall()]

            if not status_codes:
                return 0

            # 第二步：获取这些code对应的所有status
            self.cursor.execute('''
                                SELECT status
                                FROM uspto_code
                                WHERE status_code IN %s
                                ''', (status_codes,))

            all_statuses = [row[0] for row in self.cursor.fetchall()]

            # 第三步：在Python中确定最高优先级状态
            priority_groups = [
                {"Registered", "Live"},  # 最高优先级
                {"Pending"},  # 中优先级
                {"Dead", "Indifferent"}  # 最低优先级
            ]

            for group in priority_groups:
                for status in all_statuses:
                    if status in group:
                        return status

            # 如果没有匹配已知优先级，返回第一个状态
            return all_statuses[0]

        except pymysql.Error as e:
            raise RuntimeError(f"状态查询失败: {e}")
    # 更新amazon_brand数据的品牌状态
    def update_amazon_brand(self):
        db = AmazonBrand()
        brand_all = db.get_brands_by_region(region="US")
        for brand in brand_all:
            status = self.search_mark_identification(brand)
            print(status)
            db.update_brand_status(brand=brand,region='US',status=status)


if __name__ == '__main__':
    uspto_brand = UsptoBrand()
    uspto_brand.update_amazon_brand()