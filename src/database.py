"""
数据库连接管理
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base

# 加载 .env 文件中的环境变量
load_dotenv()


class Database:
    """数据库连接管理类"""
    
    def __init__(self):
        self.engine = None
        self.Session = None
        self._init_engine()
    
    def _init_engine(self):
        """初始化数据库引擎"""
        # 从环境变量获取配置
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        
        # 验证配置完整性
        if not all([db_host, db_name, db_user, db_password]):
            raise ValueError(
                "数据库配置不完整！请检查 .env 文件是否包含所有必需的配置：\n"
                "DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
            )
        
        # 构建 MySQL 连接 URL
        database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # 创建引擎
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,      # 连接前先 ping，确保连接有效
            pool_recycle=3600,       # 1小时后回收连接
            echo=False,              # 设置为 True 可以看到所有 SQL 语句（调试用）
        )
        
        # 创建 Session 类
        self.Session = sessionmaker(bind=self.engine)
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT VERSION()"))
                version = result.fetchone()[0]
                print("✓ 数据库连接成功！")
                print(f"MySQL 版本: {version}")
                return True
        except Exception as e:
            print(f"✗ 数据库连接失败: {e}")
            return False
    
    def create_tables(self):
        """创建所有数据表（仅创建不存在的表）"""
        try:
            Base.metadata.create_all(self.engine)
            print("✓ 数据表创建/确认成功！")
            # 验证关键表是否存在
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            expected_tables = [t.name for t in Base.metadata.sorted_tables]
            missing = [t for t in expected_tables if t not in existing_tables]
            if missing:
                print(f"⚠️ 以下表未创建成功: {missing}")
                return False
            print(f"  已确认 {len(expected_tables)} 张表存在: {expected_tables}")
            return True
        except Exception as e:
            print(f"✗ 创建数据表失败: {e}")
            return False
    
    def reset_program_tables(self):
        """
        删除并重建专业要求相关的数据表。

        删除范围（按依赖顺序）：
          node_courses, node_children, requirement_nodes,
          requirement_domain_memberships, requirement_domains,
          requirement_set_requirements, requirement_sets,
          requirements, user_concentrations, program_concentrations,
          program_subjects

        不影响：programs, users, user_program, courses 等表。
        注意：user_concentrations 中的用户数据会被清空。
        """
        TABLE_NAMES = [
            'node_courses',
            'node_children',
            'requirement_nodes',
            'requirement_domain_memberships',
            'requirement_domains',
            'requirement_set_requirements',
            'requirement_sets',
            'user_course_requirements',
            'requirements',
            'user_concentration',
            'program_concentrations',
            'program_subjects',
        ]
        try:
            print("正在删除专业要求相关表...")
            # 按顺序逐表删除，忽略不存在的表
            with self.engine.connect() as conn:
                conn.execute(__import__('sqlalchemy').text("SET FOREIGN_KEY_CHECKS = 0"))
                for table_name in TABLE_NAMES:
                    conn.execute(__import__('sqlalchemy').text(f"DROP TABLE IF EXISTS `{table_name}`"))
                    print(f"  已删除: {table_name}")
                conn.execute(__import__('sqlalchemy').text("SET FOREIGN_KEY_CHECKS = 1"))
                conn.commit()
            print("正在重建专业要求相关表...")
            Base.metadata.create_all(self.engine)
            print("✓ 专业要求相关表重建成功！")
            return True
        except Exception as e:
            print(f"✗ 重建专业要求相关表失败: {e}")
            return False

    def reset_tables(self):
        """删除并重建所有数据表（危险操作！会清空所有数据）"""
        try:
            print("正在删除所有表...")
            Base.metadata.drop_all(self.engine)
            print("正在重建所有表...")
            Base.metadata.create_all(self.engine)
            print("✓ 数据表重建成功！")
            return True
        except Exception as e:
            print(f"✗ 重建数据表失败: {e}")
            return False
    
    def get_session(self):
        """获取数据库会话"""
        return self.Session()
