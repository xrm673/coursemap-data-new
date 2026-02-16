"""
Course 业务逻辑服务
"""
from models import (
    Course, EnrollGroup, EnrollGroupSemester, ClassSection, 
    Meeting, Instructor, MeetingInstructor
)
from repositories import CourseRepository
from utils import extract_year, is_later_or_equal, is_later
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
        
        新逻辑（支持历史学期导入）：
        1. 对每门课程，判断是更新学期还是历史学期
        2. 更新学期：覆盖 Course 和 EnrollGroup 的所有字段
        3. 历史学期：不覆盖元数据，只补充历史数据（ClassSection 等）
        4. 始终创建/更新 EnrollGroupSemester 和 ClassSection
        
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
                'enroll_groups_updated': 0,
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
            'enroll_groups_updated': 0,
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
                
                if not course:
                    # 跳过处理
                    stats['courses_skipped_historical'] += 1
                    continue
                
                # 更新统计
                if is_historical_import:
                    stats['courses_skipped_historical'] += 1
                    print(f"  → 历史学期，不更新 Course 元数据")
                elif course.id == course_id:  # 判断是新创建还是更新
                    # 通过检查是否刚创建来判断
                    if session.is_modified(course):
                        stats['courses_updated'] += 1
                        print(f"  → 更新 Course 元数据")
                    else:
                        stats['courses_created'] += 1
                        # 创建不打印日志
                
                # 2. 处理 EnrollGroups
                enroll_groups_data = class_data.get("enrollGroups", [])
                if not enroll_groups_data:
                    print(f"  ⚠️ 警告: 课程 {course_id} 没有 enrollGroups")
                    continue
                
                print(f"  处理 {len(enroll_groups_data)} 个 EnrollGroups:")
                for eg_data in enroll_groups_data:
                    eg_stats = self._process_enroll_group(
                        session, course, eg_data, semester, semester_year, is_historical_import
                    )
                    stats['enroll_groups_created'] += eg_stats['created']
                    stats['enroll_groups_updated'] += eg_stats['updated']
                
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
            print(f"课程 - 新建: {stats['courses_created']}, 更新: {stats['courses_updated']}, 历史(跳过): {stats['courses_skipped_historical']}")
            print(f"注册组 - 新建: {stats['enroll_groups_created']}, 更新: {stats['enroll_groups_updated']}")
            if stats['failed'] > 0:
                print(f"失败: {stats['failed']}")
            print(f"{'='*60}\n")
            return stats
        except Exception as e:
            session.rollback()
            print(f"✗ 提交失败: {e}")
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
    
    def _process_enroll_group(self, session, course, eg_data, semester, semester_year, is_historical_import):
        """
        处理单个 EnrollGroup（创建、更新或补充历史数据）
        
        Args:
            session: 数据库会话
            course: Course 对象
            eg_data: enrollGroup API 数据
            semester: 学期代码
            semester_year: 学期年份
            is_historical_import: 是否是历史学期导入
        
        Returns:
            dict: {'created': 0/1, 'updated': 0/1}
        """
        stats = {'created': 0, 'updated': 0}
        
        # 1. 计算 matching_key
        matching_type, matching_key = EnrollGroupMatcher.calculate_matching_key(eg_data)
        
        # 2. 查找是否存在相同的 EnrollGroup
        existing_group = EnrollGroupMatcher.find_matching_group(
            session, course.id, matching_type, matching_key
        )
        
        # 3. 根据场景处理 EnrollGroup
        if not existing_group:
            # 场景 A：不存在，创建新的
            enroll_group = EnrollGroup(eg_data, matching_type, matching_key)
            enroll_group.course_id = course.id
            enroll_group.last_offered_semester = semester
            enroll_group.last_offered_year = semester_year
            session.add(enroll_group)
            session.flush()  # 获取 ID
            stats['created'] = 1
            # 创建不打印日志
        
        elif not is_historical_import:
            # 场景 B：存在 + 非历史导入（更新或刷新）
            enroll_group = existing_group
            # 更新元数据
            enroll_group.update_from_data(eg_data)
            # 直接更新 last_offered
            enroll_group.last_offered_semester = semester
            enroll_group.last_offered_year = semester_year
            stats['updated'] = 1
            print(f"    ✓ 更新 EnrollGroup [{matching_type}={matching_key[:30]}]")
        
        else:
            # 场景 C：存在 + 历史导入
            enroll_group = existing_group
            # 不更新任何元数据
            print(f"    → 历史学期，不更新 EnrollGroup [{matching_type}={matching_key[:30]}]")
        
        # 4. 创建/获取 EnrollGroupSemester（所有场景都需要）
        egs = session.query(EnrollGroupSemester).filter(
            EnrollGroupSemester.enroll_group_id == enroll_group.id,
            EnrollGroupSemester.semester == semester
        ).first()
        
        if not egs:
            egs = EnrollGroupSemester(semester)
            egs.enroll_group_id = enroll_group.id
            session.add(egs)
        
        # 5. 删除该 EnrollGroup 在当前 semester 的旧 ClassSections
        # （支持幂等性：重复导入同一学期会先删除旧数据）
        deleted_count = session.query(ClassSection).filter(
            ClassSection.enroll_group_id == enroll_group.id,
            ClassSection.semester == semester
        ).delete()
        if deleted_count > 0:
            print(f"      删除 {deleted_count} 个旧的 ClassSections")
        session.flush()
        
        # 6. 创建新的 ClassSections（所有场景都需要）
        class_sections_data = eg_data.get("classSections", [])
        # 创建不打印日志
        for cs_data in class_sections_data:
            self._create_class_section(session, enroll_group, cs_data, semester)
        
        return stats
    
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
