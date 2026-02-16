"""
Course 业务逻辑服务
"""
from models import (
    Course, EnrollGroup, EnrollGroupSemester, ClassSection, 
    Meeting, Instructor, MeetingInstructor
)
from repositories import CourseRepository
from .api_service import APIService
from .enroll_group_matcher import EnrollGroupMatcher


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
    
    def import_courses_from_api(self, semester, subject):
        """
        从 API 获取课程并保存到数据库
        
        新逻辑：
        1. 导入 Course（覆盖）
        2. 对每个 EnrollGroup，判断是否已存在相同的 group
        3. 如果存在则更新，不存在则创建
        4. 创建/更新 EnrollGroupSemester 记录
        5. 删除旧的 ClassSections（该 group 在当前 semester 的）
        6. 创建新的 ClassSections, Meetings, Instructors
        
        Args:
            semester: 学期代码，如 "SP26"
            subject: 学科代码，如 "MATH"
        
        Returns:
            tuple: (成功数量, 失败数量)
        """
        # 从 API 获取数据
        classes_data = self.api_service.fetch_courses(semester, subject)
        
        if not classes_data:
            print("没有获取到课程数据")
            return 0, 0
        
        print(f"\n正在处理 {len(classes_data)} 门课程...")
        
        success_count = 0
        fail_count = 0
        session = self.repository.session
        
        for class_data in classes_data:
            try:
                # 1. 创建/更新 Course
                course = Course(class_data, semester)
                course = session.merge(course)  # 覆盖旧数据
                session.flush()
                
                # 2. 处理 EnrollGroups
                enroll_groups_data = class_data.get("enrollGroups", [])
                for eg_data in enroll_groups_data:
                    self._process_enroll_group(session, course, eg_data, semester)
                
                success_count += 1
                
            except Exception as e:
                import traceback
                print(f"  ✗✗ 处理课程失败: {course.id}")
                print(f"  错误: {e}")
                print(f"  详细信息:")
                traceback.print_exc()
                fail_count += 1
                # 不要 rollback，继续处理下一门课程
        
        # 提交所有更改
        try:
            session.commit()
            print(f"\n✓ 成功导入 {success_count} 门课程")
            if fail_count > 0:
                print(f"✗ 失败 {fail_count} 门课程")
            return success_count, fail_count
        except Exception as e:
            session.rollback()
            print(f"✗ 提交失败: {e}")
            return 0, len(classes_data)
    
    def _process_enroll_group(self, session, course, eg_data, semester):
        """
        处理单个 EnrollGroup
        
        Args:
            session: 数据库会话
            course: Course 对象
            eg_data: enrollGroup API 数据
            semester: 学期代码
        """
        # 1. 计算 matching_key
        matching_type, matching_key = EnrollGroupMatcher.calculate_matching_key(eg_data)
        
        # 2. 查找是否存在相同的 EnrollGroup
        existing_group = EnrollGroupMatcher.find_matching_group(
            session, course.id, matching_type, matching_key
        )
        
        if existing_group:
            # 3a. 存在：更新字段
            existing_group.update_from_data(eg_data)
            enroll_group = existing_group
        else:
            # 3b. 不存在：创建新的
            enroll_group = EnrollGroup(eg_data, matching_type, matching_key)
            enroll_group.course_id = course.id
            session.add(enroll_group)
            session.flush()  # 获取 ID
        
        # 4. 创建/获取 EnrollGroupSemester
        egs = session.query(EnrollGroupSemester).filter(
            EnrollGroupSemester.enroll_group_id == enroll_group.id,
            EnrollGroupSemester.semester == semester
        ).first()
        
        if not egs:
            egs = EnrollGroupSemester(semester)
            egs.enroll_group_id = enroll_group.id
            session.add(egs)
        
        # 5. 删除该 EnrollGroup 在当前 semester 的旧 ClassSections
        session.query(ClassSection).filter(
            ClassSection.enroll_group_id == enroll_group.id,
            ClassSection.semester == semester
        ).delete()
        session.flush()
        
        # 6. 创建新的 ClassSections
        class_sections_data = eg_data.get("classSections", [])
        for cs_data in class_sections_data:
            self._create_class_section(session, enroll_group, cs_data, semester)
    
    def _create_class_section(self, session, enroll_group, cs_data, semester):
        """
        创建 ClassSection 及其关联的 Meetings 和 Instructors
        
        Args:
            session: 数据库会话
            enroll_group: EnrollGroup 对象
            cs_data: classSection API 数据
            semester: 学期代码
        """
        # 1. 创建 ClassSection
        class_section = ClassSection(cs_data, semester)
        class_section.enroll_group_id = enroll_group.id
        session.add(class_section)
        session.flush()
        
        # 2. 创建 Meetings
        meetings_data = cs_data.get("meetings", [])
        for meeting_data in meetings_data:
            meeting = Meeting(meeting_data)
            meeting.class_section_class_nbr = class_section.class_nbr
            meeting.class_section_semester = class_section.semester
            session.add(meeting)
            session.flush()  # 获取 meeting.id
            
            # 3. 处理 Instructors
            instructors_data = meeting_data.get("instructors", [])
            for instructor_data in instructors_data:
                # 3a. 创建/更新 Instructor（独立表）
                instructor = Instructor(instructor_data)
                instructor = session.merge(instructor)  # 更新名字（如果有变化）
                
                # 3b. 创建 MeetingInstructor 关系
                assign_seq = instructor_data.get("instrAssignSeq", 1)
                meeting_instructor = MeetingInstructor(
                    instructor.netid, 
                    assign_seq
                )
                meeting_instructor.meeting_id = meeting.id
                session.add(meeting_instructor)
    
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
