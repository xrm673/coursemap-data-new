"""
主程序入口
演示如何使用整个系统
"""
from database import Database
from repositories import CourseRepository
from services import CourseService


def main():
    """主函数"""
    print("=" * 60)
    print("Cornell 课程数据导入系统")
    print("=" * 60)
    print()
    
    # 1. 初始化数据库
    print("步骤 1: 初始化数据库连接")
    print("-" * 60)
    db = Database()
    
    # 测试连接
    if not db.test_connection():
        print("\n数据库连接失败，请检查 .env 配置")
        return
    print()
    
    # 2. 创建表（如果不存在）
    print("步骤 2: 创建数据表")
    print("-" * 60)
    db.create_tables()
    print()
    
    # 3. 初始化服务层
    print("步骤 3: 初始化服务")
    print("-" * 60)
    session = db.get_session()
    course_repo = CourseRepository(session)
    course_service = CourseService(course_repo)
    print("✓ 服务初始化完成")
    print()
    
    # 4. 从 API 导入数据
    print("步骤 4: 从 API 导入课程数据")
    print("-" * 60)
    
    # 可以修改这里的参数来导入不同学期和学科的课程
    roster = "SP26"
    subject = "MATH" 
    
    success, fail = course_service.import_courses_from_api(roster, subject)
    print()
    
    # 关闭会话
    session.close()
    
    print("=" * 60)
    print("程序执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
