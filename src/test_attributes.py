"""
测试脚本：验证 CourseAttribute 功能
"""
from database import Database
from repositories import CourseRepository
from services import CourseService


def test_course_attributes():
    """测试课程属性功能"""
    print("=" * 70)
    print("测试课程属性功能")
    print("=" * 70)
    print()
    
    # 初始化
    db = Database()
    if not db.test_connection():
        print("数据库连接失败")
        return
    
    session = db.get_session()
    repo = CourseRepository(session)
    service = CourseService(repo)
    
    # 测试 1: 查看某门课的属性
    print("测试 1: 查看 MATH1110 的属性")
    print("-" * 70)
    course = service.get_course_info("MATH1110")
    if course:
        print(f"课程: {course.id} - {course.title_short}")
        print(f"属性数量: {len(course.attributes)}")
        for attr in course.attributes:
            print(f"  • {attr.attribute_value}: {attr.attribute_type or '(无描述)'}")
    else:
        print("课程不存在（可能还没导入数据）")
    print()
    
    # 测试 2: 属性统计
    print("测试 2: 所有属性统计")
    print("-" * 70)
    stats = service.get_attribute_statistics()
    print(f"共有 {len(stats)} 种不同的属性：")
    for attr_value, count in stats[:15]:
        print(f"  {attr_value:20s} - {count:3d} 门课程")
    print()
    
    # 测试 3: 查找有特定属性的课程
    print("测试 3: 查找有 'MQR' 属性的所有课程")
    print("-" * 70)
    courses = service.get_courses_by_attribute("MQR")
    print(f"找到 {len(courses)} 门课程：")
    for i, course in enumerate(courses[:10], 1):
        attr_count = len(course.attributes)
        print(f"  {i:2d}. {course.id:12s} - {course.title_short:40s} ({attr_count} 个属性)")
    if len(courses) > 10:
        print(f"  ... 还有 {len(courses) - 10} 门课程")
    print()
    
    # 测试 4: 多属性查询
    print("测试 4: 查看有多个属性的课程")
    print("-" * 70)
    all_courses = service.list_courses_by_subject("MATH")
    multi_attr_courses = [c for c in all_courses if len(c.attributes) > 1]
    print(f"有多个属性的课程: {len(multi_attr_courses)} 门")
    for i, course in enumerate(multi_attr_courses[:5], 1):
        print(f"  {i}. {course.id} - {course.title_short}")
        for attr in course.attributes:
            print(f"     • {attr.attribute_value}: {attr.attribute_type or '(无描述)'}")
    print()
    
    session.close()
    
    print("=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    test_course_attributes()
