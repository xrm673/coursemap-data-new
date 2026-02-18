"""
Course 业务逻辑服务
"""
from models import (
    Course, EnrollGroup, ClassSection, 
    Meeting, Instructor, MeetingInstructor
)
from repositories import CourseRepository
from utils import extract_year, is_later_or_equal, is_later
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
    
    def import_courses_from_api(self, semester, subject):
        """
        从 API 获取课程并保存到数据库
        
        新逻辑（增量更新）：
        1. 对每门课程，判断 Course 是更新学期还是历史学期
        2. 更新学期：覆盖 Course 的所有元数据字段
        3. 历史学期：不覆盖 Course 元数据
        4. EnrollGroup：匹配或创建（不删除旧的）
        5. ClassSection：匹配并更新 open_status，或创建（不删除旧的）
        6. Meeting：删了重建（CASCADE 删除 MeetingInstructor）
        
        Args:
            semester: 学期代码，如 "SP26"
            subject: 学科代码，如 "MATH"
        
        Returns:
            dict: 详细的统计信息
        """
        # 从 API 获取数据
        classes_data = self.api_service.fetch_courses(semester, subject)
        
        if not classes_data:
            print("没有获取到课程数据")
            return {
                'courses_created': 0,
                'courses_updated': 0,
                'courses_skipped_historical': 0,
                'enroll_groups_created': 0,
                'enroll_groups_matched': 0,
                'class_sections_created': 0,
                'class_sections_updated': 0,
                'meetings_rebuilt': 0,
                'failed': 0
            }
        
        print(f"\n{'='*60}")
        print(f"开始导入 {semester} - {subject} 的课程数据")
        print(f"{'='*60}")
        print(f"从 API 获取到 {len(classes_data)} 门课程\n")
        
        # 统计信息
        stats = {
            'courses_created': 0,
            'courses_updated': 0,
            'courses_skipped_historical': 0,
            'enroll_groups_created': 0,
            'enroll_groups_matched': 0,
            'class_sections_created': 0,
            'class_sections_updated': 0,
            'meetings_rebuilt': 0,
            'failed': 0
        }
        
        session = self.repository.session
        semester_year = extract_year(semester)
        
        for idx, class_data in enumerate(classes_data, 1):
            try:
                course_id = class_data["subject"] + class_data["catalogNbr"]
                print(f"[{idx}/{len(classes_data)}] 处理课程: {course_id}")
                
                # 1. 处理 Course（判断是创建、更新还是历史）
                course, is_historical_import = self._process_course(
                    session, class_data, semester, semester_year
                )
                
                # 更新统计和日志
                if is_historical_import:
                    stats['courses_skipped_historical'] += 1
                    print(f"  → 历史学期，不更新 Course 元数据")
                elif session.is_modified(course):
                    stats['courses_updated'] += 1
                    print(f"  → 更新 Course 元数据")
                else:
                    stats['courses_created'] += 1
                
                # 2. 处理 EnrollGroups（匹配或创建，不删除）
                enroll_groups_data = class_data.get("enrollGroups", [])
                if not enroll_groups_data:
                    print(f"  ⚠️ 警告: 课程 {course_id} 没有 enrollGroups")
                    continue
                
                for eg_data in enroll_groups_data:
                    # 2a. 匹配或创建 EnrollGroup
                    enroll_group, is_new_eg = self._process_enroll_group(
                        session, course, eg_data, semester
                    )
                    
                    if is_new_eg:
                        stats['enroll_groups_created'] += 1
                    else:
                        stats['enroll_groups_matched'] += 1
                    
                    # 2b. 处理 ClassSections
                    class_sections_data = eg_data.get("classSections", [])
                    for cs_data in class_sections_data:
                        is_new_cs, meetings_count = self._process_class_section(
                            session, enroll_group, cs_data, semester
                        )
                        
                        if is_new_cs:
                            stats['class_sections_created'] += 1
                        else:
                            stats['class_sections_updated'] += 1
                        
                        stats['meetings_rebuilt'] += meetings_count
            
            except Exception as e:
                import traceback
                print(f"  ✗✗ 处理课程失败: {course_id if 'course_id' in locals() else 'UNKNOWN'}")
                print(f"  错误: {e}")
                print(f"  详细信息:")
                traceback.print_exc()
                stats['failed'] += 1
                # 继续处理下一门课程
        
        # 提交所有更改
        try:
            session.commit()
            print(f"\n{'='*60}")
            print(f"导入完成！统计信息：")
            print(f"{'='*60}")
            print(f"课程 - 新建: {stats['courses_created']}, 更新: {stats['courses_updated']}, 历史(跳过元数据): {stats['courses_skipped_historical']}")
            print(f"注册组 - 新建: {stats['enroll_groups_created']}, 匹配: {stats['enroll_groups_matched']}")
            print(f"班级 - 新建: {stats['class_sections_created']}, 更新: {stats['class_sections_updated']}")
            print(f"Meeting - 重建: {stats['meetings_rebuilt']}")
            if stats['failed'] > 0:
                print(f"失败: {stats['failed']}")
            print(f"{'='*60}\n")
            return stats
        except Exception as e:
            session.rollback()
            print(f"✗ 提交失败: {e}")
            import traceback
            traceback.print_exc()
            stats['failed'] = len(classes_data)
            return stats
    
    def _process_course(self, session, class_data, semester, semester_year):
        """
        处理单个 Course（创建、更新或跳过）
        
        Args:
            session: 数据库会话
            class_data: 课程 API 数据
            semester: 学期代码
            semester_year: 学期年份
        
        Returns:
            tuple: (course对象, is_historical_import)
        """
        course_id = class_data["subject"] + class_data["catalogNbr"]
        existing_course = session.query(Course).get(course_id)
        
        # 场景 A：Course 不存在，创建新的
        if not existing_course:
            course = Course(class_data, semester)
            course.last_offered_semester = semester
            course.last_offered_year = semester_year
            session.add(course)
            session.flush()
            return course, False  # 不是历史导入
        
        # 场景 B：Course 存在 + 导入学期 >= 现有学期（更新或刷新）
        elif is_later_or_equal(semester, existing_course.last_offered_semester):
            course = existing_course
            # 覆盖所有元数据
            course.update_from_data(class_data)
            # 直接更新 last_offered（无论是否更晚，赋相同值也无害）
            course.last_offered_semester = semester
            course.last_offered_year = semester_year
            return course, False  # 不是历史导入
        
        # 场景 C：Course 存在 + 导入历史学期（< 现有学期）
        else:
            # 不更新任何 Course 字段
            return existing_course, True  # 是历史导入
    
    def _process_enroll_group(self, session, course, eg_data, semester):
        """
        匹配或创建 EnrollGroup
        
        Args:
            session: 数据库会话
            course: Course 对象
            eg_data: enrollGroup API 数据
            semester: 学期代码
        
        Returns:
            tuple: (EnrollGroup对象, is_new)
        """
        # 1. 提取 first_section_number
        class_sections_data = eg_data.get("classSections", [])
        if not class_sections_data:
            raise ValueError("EnrollGroup 没有 classSections")
        
        first_section_number = class_sections_data[0].get("section")
        if not first_section_number:
            raise ValueError("第一个 ClassSection 没有 section 字段")
        
        # 2. 尝试匹配现有的 EnrollGroup
        existing_eg = session.query(EnrollGroup).filter(
            EnrollGroup.course_id == course.id,
            EnrollGroup.semester == semester,
            EnrollGroup.first_section_number == first_section_number
        ).first()
        
        if existing_eg:
            # 3a. 已存在：保持不变（根据需求，这些字段几乎不更新）
            print(f"  → EnrollGroup 已存在 (ID={existing_eg.id}, first_section={first_section_number})")
            return existing_eg, False
        else:
            # 3b. 不存在：创建新的（不打印日志）
            topic = self._extract_topic(eg_data)
            enroll_group = EnrollGroup(eg_data, semester, first_section_number, topic)
            enroll_group.course_id = course.id
            session.add(enroll_group)
            session.flush()  # 获取 ID
            return enroll_group, True
    
    def _process_class_section(self, session, enroll_group, cs_data, semester):
        """
        匹配或创建 ClassSection，并处理 Meeting
        
        Args:
            session: 数据库会话
            enroll_group: EnrollGroup 对象
            cs_data: classSection API 数据
            semester: 学期代码
        
        Returns:
            tuple: (is_new, meetings_count)
        """
        # 1. 提取 section_number
        section_number = cs_data.get("section")
        if not section_number:
            raise ValueError("ClassSection 没有 section 字段")
        
        # 2. 尝试匹配现有的 ClassSection
        existing_cs = session.query(ClassSection).filter(
            ClassSection.enroll_group_id == enroll_group.id,
            ClassSection.section_number == section_number
        ).first()
        
        if existing_cs:
            # 3a. 已存在：更新 open_status
            old_status = existing_cs.open_status
            new_status = cs_data.get("openStatus")
            
            if old_status != new_status:
                existing_cs.open_status = new_status
                print(f"    → Section {section_number}: {old_status} → {new_status}")
            # 如果状态未变，不打印
            
            # 4. 删了重建 Meeting
            meetings_count = self._rebuild_meetings(session, existing_cs, cs_data)
            
            return False, meetings_count
        else:
            # 3b. 不存在：创建新的（不打印日志）
            class_section = ClassSection(cs_data, semester)
            class_section.enroll_group_id = enroll_group.id
            session.add(class_section)
            session.flush()
            
            # 4. 创建 Meeting
            meetings_count = self._create_meetings(session, class_section, cs_data)
            
            return True, meetings_count
    
    def _rebuild_meetings(self, session, class_section, cs_data):
        """
        删了重建 Meeting（CASCADE 删除 MeetingInstructor）
        
        Args:
            session: 数据库会话
            class_section: ClassSection 对象
            cs_data: classSection API 数据
        
        Returns:
            int: 创建的 Meeting 数量
        """
        # 1. 删除旧的 Meeting（CASCADE 会自动删除 MeetingInstructor）
        deleted_count = session.query(Meeting).filter(
            Meeting.class_section_id == class_section.id
        ).delete()
        
        if deleted_count > 0:
            print(f"      删除 {deleted_count} 个旧 Meeting")
        
        session.flush()
        
        # 2. 创建新的 Meeting
        meetings_count = self._create_meetings(session, class_section, cs_data)
        
        return meetings_count
    
    def _create_meetings(self, session, class_section, cs_data):
        """
        创建 Meeting 和 Instructor
        
        Args:
            session: 数据库会话
            class_section: ClassSection 对象
            cs_data: classSection API 数据
        
        Returns:
            int: 创建的 Meeting 数量
        """
        meetings_data = cs_data.get("meetings", [])
        meetings_count = 0
        
        for meeting_data in meetings_data:
            meeting = Meeting(meeting_data)
            meeting.class_section_id = class_section.id
            session.add(meeting)
            session.flush()  # 获取 meeting.id
            meetings_count += 1
            
            # 创建 Instructor 关系
            instructors_data = meeting_data.get("instructors", [])
            for instructor_data in instructors_data:
                # 创建/更新 Instructor（独立表）
                instructor = Instructor(instructor_data)
                instructor = session.merge(instructor)  # 更新名字（如果有变化）
                
                # 创建 MeetingInstructor 关系
                assign_seq = instructor_data.get("instrAssignSeq", 1)
                meeting_instructor = MeetingInstructor(
                    instructor.netid, 
                    assign_seq
                )
                meeting_instructor.meeting_id = meeting.id
                session.add(meeting_instructor)
        
        # 创建 Meeting 不打印日志
        return meetings_count
    
    def _extract_topic(self, eg_data):
        """
        从 enrollGroup 的 classSections 中提取 topic
        
        取第一个有 topicDescription 的 classSection 的值
        
        Args:
            eg_data: enrollGroup API 数据
            
        Returns:
            str 或 None
        """
        class_sections_data = eg_data.get("classSections", [])
        for cs_data in class_sections_data:
            topic = cs_data.get("topicDescription", "").strip()
            if topic:
                return topic
        return None
    
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
