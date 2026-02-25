"""
主程序入口
支持命令行参数灵活导入课程数据
"""
import sys
import argparse
from database import Database
from repositories import CourseRepository
from services import CourseService


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Cornell 课程数据导入系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python src/main.py --semester SP26                      # 导入 SP26 所有课程
  python src/main.py --semester FA26 --subjects INFO CS   # 只导入指定学科
  python src/main.py --semester SP26 --skip-combined      # 跳过 combined 解析
        """
    )
    
    parser.add_argument(
        '--semester',
        type=str,
        required=True,
        help='学期代码，如 SP26, FA25, WI26'
    )
    
    parser.add_argument(
        '--subjects',
        nargs='+',
        help='指定要导入的学科列表（不指定则导入全部），如: INFO CS MATH'
    )
    
    parser.add_argument(
        '--skip-combined',
        action='store_true',
        help='跳过 Combined Groups 解析（加快导入速度）'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    print("=" * 60)
    print("Cornell 课程数据导入系统")
    print("=" * 60)
    print(f"学期: {args.semester}")
    if args.subjects:
        print(f"学科: {', '.join(args.subjects)}")
    else:
        print("学科: 全部")
    if args.skip_combined:
        print("模式: 跳过 Combined Groups 解析")
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
    if not db.create_tables():
        print("\n数据表创建失败，程序终止")
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
    
    # 3.5. 初始化 Subject 数据
    print("步骤 3.5: 初始化 Subject 数据")
    print("-" * 60)
    subject_stats = course_service.initialize_subjects(args.semester)
    
    # 4. 从 API 导入数据
    print("\n步骤 4: 从 API 导入课程数据")
    print("-" * 60)
    
    if args.subjects:
        # 导入指定学科
        print(f"导入指定学科: {', '.join(args.subjects)}\n")
        for subject in args.subjects:
            try:
                stats = course_service.import_courses_from_api(args.semester, subject)
            except Exception as e:
                print(f"✗ 导入 {subject} 失败: {e}")
                continue
    else:
        # 导入所有学科（只导入该学期实际存在的）
        print("导入所有学科\n")
        # 传入该学期实际存在的 subject 列表
        subject_values = subject_stats.get('subjects', [])
        all_stats = course_service.import_all_subjects(args.semester, subject_values)
    
    # 5. 解析 Combined Course 关系
    if not args.skip_combined:
        print("\n步骤 5: 解析 Combined Course 关系")
        print("-" * 60)
        combined_stats = course_service.resolve_combined_groups(args.semester)
    else:
        print("\n步骤 5: 跳过 Combined Course 解析")
        print("-" * 60)
        print("已跳过")
    
    # 关闭会话
    session.close()
    
    print("\n" + "=" * 60)
    print("程序执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
