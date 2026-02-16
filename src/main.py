"""
主程序入口
演示如何使用整个系统
"""
import sys
from database import Database
from repositories import CourseRepository
from services import CourseService


def main():
    """主函数"""
    print("=" * 60)
    print("Cornell 课程数据导入系统")
    print("=" * 60)
    print()
    
    # 检查是否需要重建表
    reset_mode = "--reset" in sys.argv
    
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
    if reset_mode:
        print("⚠️ 重建模式：将删除并重建所有表")
        if not db.reset_tables():
            print("\n数据表重建失败，程序终止")
            return
    else:
        if not db.create_tables():
            print("\n数据表创建失败，程序终止")
            print("提示：如果表结构已变更，请使用 --reset 参数重建表")
            return
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
    semester = "SP26"
    subject = "INFO" 
    
    stats = course_service.import_courses_from_api(semester, subject)
    
    # 关闭会话
    session.close()
    
    print("=" * 60)
    print("程序执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
