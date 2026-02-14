"""
Course 业务逻辑服务
"""
from models import Course
from repositories import CourseRepository
from .api_service import APIService


class CourseService:
    """课程业务逻辑类"""
    
    def __init__(self, repository):
        """
        初始化服务
        
        Args:
            repository: CourseRepository 实例
        """
        self.repository = repository
        self.api_service = APIService()
    
    def import_courses_from_api(self, roster, subject):
        """
        从 API 获取课程并保存到数据库
        
        Args:
            roster: 学期代码，如 "SP26"
            subject: 学科代码，如 "MATH"
        
        Returns:
            tuple: (成功数量, 失败数量)
        """
        # 从 API 获取数据
        classes_data = self.api_service.fetch_courses(roster, subject)
        
        if not classes_data:
            print("没有获取到课程数据")
            return 0, 0
        
        # 转换为 Course 对象
        courses = []
        for class_data in classes_data:
            try:
                course = Course(class_data)
                courses.append(course)
            except Exception as e:
                print(f"转换课程数据失败: {e}")
                print(f"问题数据: {class_data.get('subject', '?')}{class_data.get('catalogNbr', '?')}")
        
        # 批量保存到数据库
        if courses:
            print(f"\n正在保存 {len(courses)} 门课程到数据库...")
            success, fail = self.repository.save_batch(courses)
            print(f"✓ 成功保存 {success} 门课程")
            if fail > 0:
                print(f"✗ 失败 {fail} 门课程")
            return success, fail
        else:
            return 0, 0
    
    def get_course_info(self, course_id):
        """
        获取课程信息
        
        Args:
            course_id: 课程 ID
        
        Returns:
            Course 对象或 None
        """
        return self.repository.get_by_id(course_id)
    
    def list_courses_by_subject(self, subject):
        """
        列出某学科的所有课程
        
        Args:
            subject: 学科代码
        
        Returns:
            Course 对象列表
        """
        return self.repository.get_by_subject(subject)
    
    def get_statistics(self):
        """
        获取数据库统计信息
        
        Returns:
            dict: 统计信息
        """
        total_courses = self.repository.count()
        return {
            'total_courses': total_courses
        }
    
    def get_courses_by_attribute(self, attribute_value):
        """
        查找有某个 attribute 的所有课程
        
        Args:
            attribute_value: 属性值 (如 "MQR", "CA-AS")
        
        Returns:
            Course 对象列表
        """
        return self.repository.get_courses_by_attribute(attribute_value)
    
    def get_attribute_statistics(self):
        """
        获取所有 attribute 的统计信息
        
        Returns:
            list: [(attribute_value, count), ...] 按课程数量降序
        """
        return self.repository.get_attribute_statistics()
