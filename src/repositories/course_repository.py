"""
Course 数据访问层
负责所有与 Course 表相关的数据库操作
"""
from sqlalchemy.exc import SQLAlchemyError
from models import Course, CourseAttribute


class CourseRepository:
    """Course 数据访问类"""
    
    def __init__(self, session):
        """
        初始化 Repository
        
        Args:
            session: SQLAlchemy 数据库会话
        """
        self.session = session
    
    def save(self, course):
        """
        保存或更新课程
        
        Args:
            course: Course 对象
        
        Returns:
            bool: 是否保存成功
        """
        try:
            self.session.merge(course)  # merge 会自动判断是插入还是更新
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"保存课程失败 {course.id}: {e}")
            return False
    
    def save_batch(self, courses):
        """
        批量保存课程
        
        Args:
            courses: Course 对象列表
        
        Returns:
            tuple: (成功数量, 失败数量)
        """
        success_count = 0
        fail_count = 0
        
        for course in courses:
            try:
                self.session.merge(course)
                success_count += 1
            except SQLAlchemyError as e:
                print(f"保存课程失败 {course.id}: {e}")
                fail_count += 1
        
        try:
            self.session.commit()
            return success_count, fail_count
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"批量提交失败: {e}")
            return 0, len(courses)
    
    def get_by_id(self, course_id):
        """
        根据 ID 获取课程
        
        Args:
            course_id: 课程 ID (如 "MATH1110")
        
        Returns:
            Course 对象或 None
        """
        return self.session.query(Course).filter(Course.id == course_id).first()
    
    def get_by_subject(self, subject):
        """
        根据学科获取所有课程
        
        Args:
            subject: 学科代码 (如 "MATH")
        
        Returns:
            Course 对象列表
        """
        return self.session.query(Course).filter(Course.subject == subject).all()
    
    def get_all(self):
        """
        获取所有课程
        
        Returns:
            Course 对象列表
        """
        return self.session.query(Course).all()
    
    def count(self):
        """
        获取课程总数
        
        Returns:
            int: 课程数量
        """
        return self.session.query(Course).count()
    
    def exists(self, course_id):
        """
        检查课程是否存在
        
        Args:
            course_id: 课程 ID
        
        Returns:
            bool: 是否存在
        """
        return self.session.query(Course).filter(Course.id == course_id).count() > 0
    
    def get_courses_by_attribute(self, attribute_value):
        """
        查找有某个 attribute 的所有课程
        
        Args:
            attribute_value: 属性值 (如 "MQR", "CA-AS")
        
        Returns:
            Course 对象列表
        """
        return self.session.query(Course).join(CourseAttribute).filter(
            CourseAttribute.attribute_value == attribute_value
        ).all()
    
    def get_attribute_statistics(self):
        """
        获取所有 attribute 的统计信息
        
        Returns:
            list: [(attribute_value, count), ...] 按课程数量降序
        """
        from sqlalchemy import func
        
        results = self.session.query(
            CourseAttribute.attribute_value,
            func.count(CourseAttribute.course_id).label('course_count')
        ).group_by(
            CourseAttribute.attribute_value
        ).order_by(
            func.count(CourseAttribute.course_id).desc()
        ).all()
        
        return [(attr_value, count) for attr_value, count in results]