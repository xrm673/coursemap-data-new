"""
Course 业务逻辑服务
"""
import json
from models import (
    Course, EnrollGroup, ClassSection, 
    Meeting, Instructor, MeetingInstructor, CombinedGroup, Subject
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
            
            # 更新 combined_with_json（如果 API 数据变了）
            simple_combinations = eg_data.get("simpleCombinations", [])
            new_json = json.dumps(simple_combinations) if simple_combinations else None
            if new_json != existing_eg.combined_with_json:
                existing_eg.combined_with_json = new_json
            
            return existing_eg, False
        else:
            # 3b. 不存在：创建新的（不打印日志）
            topic = self._extract_topic(eg_data)
            enroll_group = EnrollGroup(eg_data, semester, first_section_number, topic)
            enroll_group.course_id = course.id
            
            # 存储 simpleCombinations
            simple_combinations = eg_data.get("simpleCombinations", [])
            if simple_combinations:
                enroll_group.combined_with_json = json.dumps(simple_combinations)
            
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
    
    def resolve_combined_groups(self, semester):
        """
        解析某学期的所有 combined 关系，建立 CombinedGroup
        
        流程：
        1. 查询所有有 combined_with_json 的 EnrollGroup
        2. 解析 JSON，尝试匹配目标 EnrollGroup
        3. 使用 Union-Find 算法，将所有关联的 EG 分组
        4. 为每个组创建 CombinedGroup，更新 EG 的 combined_group_id
        
        Args:
            semester: 学期代码，如 "SP26"
        
        Returns:
            dict: 统计信息
        """
        session = self.repository.session
        
        print(f"\n{'='*60}")
        print(f"解析 {semester} 的 Combined Course 关系")
        print(f"{'='*60}")
        
        # 1. 获取所有有 combined 数据的 EnrollGroup
        enroll_groups = session.query(EnrollGroup).filter(
            EnrollGroup.semester == semester,
            EnrollGroup.combined_with_json.isnot(None)
        ).all()
        
        if not enroll_groups:
            print("没有需要处理 combined 关系的 EnrollGroup")
            return {'groups_created': 0, 'matches_success': 0, 'matches_failed': 0}
        
        print(f"找到 {len(enroll_groups)} 个需要处理 combined 关系的 EnrollGroup\n")
        
        # 2. 构建匹配关系（图的边）
        edges = []  # [(eg_id_1, eg_id_2), ...]
        match_stats = {'success': 0, 'failed': 0}
        
        for eg in enroll_groups:
            try:
                combined_list = json.loads(eg.combined_with_json)
            except json.JSONDecodeError:
                print(f"  ⚠️ JSON 解析失败: {eg.course_id} EG#{eg.id}")
                continue
            
            for combined_course in combined_list:
                target_subject = combined_course.get('subject')
                target_catalog = combined_course.get('catalogNbr')
                
                if not target_subject or not target_catalog:
                    continue
                
                target_course_id = target_subject + target_catalog
                
                # 尝试匹配目标 EnrollGroup
                matched_eg = self._find_matching_enroll_group(
                    session, target_course_id, semester, eg
                )
                
                if matched_eg:
                    edges.append((eg.id, matched_eg.id))
                    match_stats['success'] += 1
                else:
                    print(f"  ⚠️ 无法匹配: {eg.course_id} EG#{eg.id} → {target_course_id}")
                    match_stats['failed'] += 1
        
        print(f"\n匹配统计: 成功 {match_stats['success']}, 失败 {match_stats['failed']}")
        
        # 3. 使用 Union-Find 分组
        groups = self._find_connected_components(edges)
        
        print(f"找到 {len(groups)} 个 Combined Group\n")
        
        # 4. 创建 CombinedGroup 并更新 EnrollGroup
        for idx, group_egs in enumerate(groups, 1):
            # 创建新的 CombinedGroup
            combined_group = CombinedGroup(semester=semester)
            session.add(combined_group)
            session.flush()
            
            # 更新所有成员的 combined_group_id
            course_info = []
            for eg_id in group_egs:
                eg = session.query(EnrollGroup).get(eg_id)
                eg.combined_group_id = combined_group.id
                course_info.append(f"{eg.course_id} (EG#{eg.id})")
            
            # 打印组信息
            print(f"  Combined Group {combined_group.id}: {', '.join(course_info)}")
        
        session.commit()
        print(f"\n{'='*60}")
        print(f"✓ Combined 关系解析完成！")
        print(f"{'='*60}\n")
        
        return {
            'groups_created': len(groups),
            'matches_success': match_stats['success'],
            'matches_failed': match_stats['failed']
        }
    
    def _find_matching_enroll_group(self, session, target_course_id, semester, source_eg):
        """
        按优先级匹配目标 EnrollGroup
        
        优先级：
        1. Topic 相同（非空）
        2. first_section_number 相同
        3. 目标课程只有一个 EnrollGroup
        
        Args:
            session: 数据库会话
            target_course_id: 目标课程 ID
            semester: 学期代码
            source_eg: 源 EnrollGroup
        
        Returns:
            EnrollGroup 或 None
        """
        # 查询目标课程的所有 EnrollGroup
        target_egs = session.query(EnrollGroup).filter(
            EnrollGroup.course_id == target_course_id,
            EnrollGroup.semester == semester
        ).all()
        
        if not target_egs:
            return None
        
        # 优先级 1: Topic 匹配（都非空且相同）
        if source_eg.topic:
            for target_eg in target_egs:
                if target_eg.topic == source_eg.topic:
                    return target_eg
        
        # 优先级 2: first_section_number 匹配
        for target_eg in target_egs:
            if target_eg.first_section_number == source_eg.first_section_number:
                return target_eg
        
        # 优先级 3: 只有一个 EnrollGroup
        if len(target_egs) == 1:
            return target_egs[0]
        
        # 匹配失败
        return None
    
    def _find_connected_components(self, edges):
        """
        使用 Union-Find 算法找到所有连通分量
        
        Args:
            edges: [(eg_id_1, eg_id_2), ...]
        
        Returns:
            [set(eg_id, ...), ...]  每个 set 是一个组
        """
        parent = {}
        
        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])  # 路径压缩
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # 建立并查集
        for x, y in edges:
            union(x, y)
        
        # 分组
        groups = {}
        for node in parent:
            root = find(node)
            if root not in groups:
                groups[root] = set()
            groups[root].add(node)
        
        return list(groups.values())
    
    def initialize_subjects(self, roster):
        """
        从 API 获取所有 subject 并存入数据库
        如果已存在则跳过
        
        Args:
            roster: 学期代码，如 "SP26"
        
        Returns:
            dict: 统计信息 + subjects 列表
        """
        session = self.repository.session
        
        print(f"\n{'='*60}")
        print(f"初始化 Subject 数据")
        print(f"{'='*60}")
        
        # 1. 从 API 获取 subjects
        subjects_data = self.api_service.fetch_subjects(roster)
        
        if not subjects_data:
            print("没有获取到 Subject 数据")
            return {'created': 0, 'skipped': 0, 'subjects': []}
        
        print(f"从 API 获取到 {len(subjects_data)} 个 Subject\n")
        
        # 2. 遍历插入（已存在则跳过）
        created_count = 0
        skipped_count = 0
        subject_values = []  # 记录这个学期的所有 subject values
        
        for subject_data in subjects_data:
            value = subject_data['value']
            subject_values.append(value)  # 记录
            
            # 检查是否已存在
            existing = session.query(Subject).get(value)
            
            if existing:
                skipped_count += 1
                continue  # 跳过
            
            # 创建新的 Subject
            subject = Subject(
                value=value,
                description=subject_data['descr'],
                description_formal=subject_data['descrformal']
            )
            session.add(subject)
            created_count += 1
        
        session.commit()
        
        print(f"创建: {created_count} 个")
        print(f"跳过: {skipped_count} 个")
        print(f"总计: {created_count + skipped_count} 个")
        print(f"{'='*60}\n")
        
        return {
            'created': created_count,
            'skipped': skipped_count,
            'subjects': subject_values  # 返回该学期的 subject 列表
        }
    
    def import_all_subjects(self, semester, subject_values=None):
        """
        导入某学期的所有学科课程
        
        Args:
            semester: 学期代码，如 "SP26"
            subject_values: 可选，指定要导入的 subject 列表。
                           如果不提供，则从数据库查询所有 subjects
        
        Returns:
            dict: 统计信息
        """
        session = self.repository.session
        
        print(f"\n{'='*60}")
        print(f"导入所有学科的 {semester} 课程")
        print(f"{'='*60}")
        
        # 1. 获取要导入的 Subject 列表
        if subject_values:
            # 使用提供的 subject 列表（该学期实际存在的）
            subjects = session.query(Subject).filter(
                Subject.value.in_(subject_values)
            ).order_by(Subject.value).all()
            print(f"根据 API 数据，准备导入 {len(subjects)} 个学科的课程")
        else:
            # 从数据库查询所有 Subject
            subjects = session.query(Subject).order_by(Subject.value).all()
            print(f"准备导入数据库中所有 {len(subjects)} 个学科的课程")
        
        print()
        
        # 2. 统计信息
        total_stats = {
            'subjects_total': len(subjects),
            'subjects_success': 0,
            'subjects_failed': 0,
            'courses_total': 0,
            'enroll_groups_total': 0,
            'class_sections_total': 0
        }
        
        # 3. 遍历每个 Subject
        for idx, subject in enumerate(subjects, 1):
            print(f"\n{'='*60}")
            print(f"[{idx}/{len(subjects)}] {subject.value} - {subject.description}")
            print(f"进度: {idx/len(subjects)*100:.1f}%")
            print(f"{'='*60}")
            
            try:
                # 导入该 Subject 的课程
                stats = self.import_courses_from_api(semester, subject.value)
                
                # 累加统计
                total_stats['subjects_success'] += 1
                total_stats['courses_total'] += (
                    stats.get('courses_created', 0) + 
                    stats.get('courses_updated', 0) + 
                    stats.get('courses_skipped_historical', 0)
                )
                total_stats['enroll_groups_total'] += (
                    stats.get('enroll_groups_created', 0) + 
                    stats.get('enroll_groups_matched', 0)
                )
                total_stats['class_sections_total'] += (
                    stats.get('class_sections_created', 0) + 
                    stats.get('class_sections_updated', 0)
                )
                
            except Exception as e:
                print(f"\n✗✗ 导入失败: {e}")
                import traceback
                traceback.print_exc()
                total_stats['subjects_failed'] += 1
                continue  # 继续下一个 Subject
        
        # 4. 打印总结
        print(f"\n{'='*60}")
        print(f"所有学科导入完成")
        print(f"{'='*60}")
        print(f"学科 - 成功: {total_stats['subjects_success']}/{total_stats['subjects_total']}, 失败: {total_stats['subjects_failed']}")
        print(f"课程总数: {total_stats['courses_total']}")
        print(f"注册组总数: {total_stats['enroll_groups_total']}")
        print(f"班级总数: {total_stats['class_sections_total']}")
        print(f"{'='*60}\n")
        
        return total_stats