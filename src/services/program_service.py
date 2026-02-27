"""
Program 业务逻辑服务
负责从 YAML 文件导入专业要求数据
"""
import json
import os
import yaml
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator
from models import (
    Course, Program, ProgramSubject,
    Requirement, RequirementSet, RequirementSetRequirement,
    RequirementDomain, RequirementDomainMembership,
    RequirementNode, NodeChild, NodeCourse,
    EnrollGroup, CombinedGroup
)
from utils.semester_utils import parse_semester


_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),       # src/services/
    '..', '..', 'data', 'programs', 'schema.json'
)


def _load_schema():
    """加载 JSON Schema（只读一次，缓存在模块级别）"""
    path = os.path.normpath(_SCHEMA_PATH)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


_SCHEMA = None  # 延迟加载


class ProgramService:
    """专业要求导入服务"""

    @staticmethod
    def validate_yaml(yaml_path):
        """
        校验一个 program YAML 文件是否符合 schema。

        Args:
            yaml_path: YAML 文件路径

        Returns:
            list[str]: 校验错误列表，空列表表示通过

        Raises:
            FileNotFoundError: YAML 或 schema 文件不存在
        """
        global _SCHEMA
        if _SCHEMA is None:
            _SCHEMA = _load_schema()

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        validator = Draft7Validator(_SCHEMA)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

        messages = []
        for err in errors:
            path = ' -> '.join(str(p) for p in err.absolute_path) or '(root)'
            messages.append(f"  [{path}] {err.message}")

        return messages

    def __init__(self, session):
        """
        初始化服务
        
        Args:
            session: SQLAlchemy 数据库会话
        """
        self.session = session
    
    def import_from_yaml(self, yaml_path):
        """
        从 YAML 文件导入专业要求数据
        
        流程：
        1. 删除该专业的现有数据（clean re-import）
        2. 创建 Program
        3. 创建 Requirements（root_node_id 暂为 NULL）
        4. 为每个 Requirement 创建 Node 树
        5. 回填 root_node_id
        6. 创建 RequirementSets
        7. 创建 RequirementDomains
        8. 提交
        
        Args:
            yaml_path: YAML 文件路径
        
        Returns:
            dict: 统计信息
        """
        # 读取 YAML
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 校验 schema
        errors = ProgramService.validate_yaml(yaml_path)
        if errors:
            error_msg = '\n'.join(errors)
            raise ValueError(
                f"YAML 文件校验失败：{yaml_path}\n{error_msg}"
            )

        program_data = data['program']
        requirements_data = data.get('requirements', [])
        program_id = program_data['id']
        
        print(f"\n{'='*60}")
        print(f"导入专业: {program_id} - {program_data['name']}")
        print(f"{'='*60}")
        
        # 统计信息
        stats = {
            'program_id': program_id,
            'requirements': 0,
            'nodes': 0,
            'node_courses': 0,
            'combined_courses': 0,
            'requirement_sets': 0,
            'domains': 0,
            'courses_not_found': []
        }
        
        # 1. 删除现有数据
        self._delete_program(program_id)
        
        # 2. 创建 Program
        program = Program(
            id=program_id,
            name=program_data['name'],
            type=program_data['type'],
            year_dependent=program_data.get('year_dependent', False),
            major_dependent=program_data.get('major_dependent', False),
            college_dependent=program_data.get('college_dependent', False),
            concentration_dependent=program_data.get('concentration_dependent', False),
            onboarding_courses=program_data.get('onboarding_courses')
        )
        self.session.add(program)
        self.session.flush()
        print(f"✓ 创建 Program: {program}")
        
        # 3. 创建 Requirements（root_node_id 暂为 NULL）
        for req_data in requirements_data:
            requirement = Requirement(
                id=req_data['id'],
                program_id=program_id,
                name=req_data['name'],
                ui_type=req_data['ui_type'],
                description=req_data.get('description')
            )
            self.session.add(requirement)
            stats['requirements'] += 1
        
        self.session.flush()
        print(f"✓ 创建 {stats['requirements']} 个 Requirements")
        
        # 4. 为每个 Requirement 创建 Node 树 & 5. 回填 root_node_id
        for req_data in requirements_data:
            req_id = req_data['id']
            node_data = req_data['root_node']
            
            # 递归创建节点树
            counter = [0]  # 用列表包装以便在递归中共享
            root_node = self._create_node_tree(req_id, node_data, counter, stats)
            
            # 回填 root_node_id
            requirement = self.session.query(Requirement).get(req_id)
            requirement.root_node_id = root_node.id
            
            print(f"  → {req_id}: 根节点 {root_node.id}, 共 {counter[0]} 个节点")
        
        self.session.flush()
        
        # 6. 创建 RequirementSets
        requirement_sets_data = program_data.get('requirement_sets', [])
        for rs_data in requirement_sets_data:
            self._create_requirement_set(rs_data, program_id)
            stats['requirement_sets'] += 1
        
        self.session.flush()
        print(f"✓ 创建 {stats['requirement_sets']} 个 RequirementSets")
        
        # 7. 创建 ProgramSubjects
        relevant_subjects = program_data.get('relevant_subjects', [])
        for subject_id in relevant_subjects:
            self.session.add(ProgramSubject(
                program_id=program_id,
                subject_id=subject_id
            ))
        self.session.flush()
        print(f"✓ 关联 {len(relevant_subjects)} 个 Subjects")

        # 9. 创建 RequirementDomains
        conflict_domains_data = program_data.get('conflict_domains', [])
        for domain_members in conflict_domains_data:
            self._create_conflict_domain(domain_members, program_id)
            stats['domains'] += 1

        self.session.flush()
        print(f"✓ 创建 {stats['domains']} 个 Conflict Domains")

        # 10. 提交
        try:
            self.session.commit()
            print(f"\n{'='*60}")
            print(f"✓ 导入完成！")
            print(f"{'='*60}")
            print(f"  Requirements: {stats['requirements']}")
            print(f"  Nodes: {stats['nodes']}")
            print(f"  Node-Course 关联: {stats['node_courses']} (其中 combined: {stats['combined_courses']})")
            print(f"  RequirementSets: {stats['requirement_sets']}")
            print(f"  Conflict Domains: {stats['domains']}")
            if stats['courses_not_found']:
                print(f"  ⚠️ 未找到的课程: {stats['courses_not_found']}")
            print(f"{'='*60}\n")
            return stats
        except Exception as e:
            self.session.rollback()
            print(f"✗ 提交失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _delete_program(self, program_id):
        """
        删除某个专业的所有数据（用于 clean re-import）
        
        Args:
            program_id: 专业 ID
        """
        program = self.session.query(Program).get(program_id)
        if not program:
            print(f"  专业 {program_id} 不存在，跳过删除")
            return
        
        # 先清除 circular FK（root_node_id）
        for req in program.requirements:
            req.root_node_id = None
        self.session.flush()
        
        # 删除 Program（cascade 会删除所有关联数据）
        self.session.delete(program)
        self.session.flush()
        print(f"  已删除旧数据: {program_id}")
    
    def _create_node_tree(self, requirement_id, node_data, counter, stats):
        """
        递归创建节点树
        
        Args:
            requirement_id: 所属 requirement ID
            node_data: 节点 YAML 数据
            counter: 节点计数器 [int]，用于生成 ID
            stats: 统计信息字典
        
        Returns:
            RequirementNode: 创建的节点
        """
        # 生成 node ID
        if counter[0] == 0:
            node_id = f"{requirement_id}_root"
        else:
            node_id = f"{requirement_id}_{counter[0]}"
        counter[0] += 1
        
        # 创建节点
        node = RequirementNode(
            id=node_id,
            requirement_id=requirement_id,
            type=node_data['type'],
            title=node_data.get('title'),
            pick_count=node_data['pick']
        )
        self.session.add(node)
        self.session.flush()
        stats['nodes'] += 1
        
        if node_data['type'] == 'GROUP':
            # GROUP 节点：递归创建子节点
            children_data = node_data.get('children', [])
            for idx, child_data in enumerate(children_data):
                child_node = self._create_node_tree(
                    requirement_id, child_data, counter, stats
                )
                # 创建父子关系
                node_child = NodeChild(
                    parent_node_id=node.id,
                    child_node_id=child_node.id,
                    position=idx
                )
                self.session.add(node_child)
        
        elif node_data['type'] == 'COURSE_SET':
            # COURSE_SET 节点：解析 query，关联课程
            query = node_data.get('query', {})
            course_ids = self._resolve_query(query)
            excluded = set(query.get('excluded', []))
            course_overrides = query.get('course_overrides', {})
            
            # 已插入的 (course_id, topic) 集合，用于去重
            inserted = {}  # key=(course_id, topic) -> NodeCourse object
            
            # --- 第一轮：插入 query 直接匹配的课程（is_primary=True）---
            for course_id in course_ids:
                course = self.session.query(Course).get(course_id)
                if not course:
                    stats['courses_not_found'].append(course_id)
                    print(f"    ⚠️ 课程不存在: {course_id}")
                    continue
                
                overrides = course_overrides.get(course_id, {})
                topics = overrides.get('topics', [])
                comment = overrides.get('comment')
                recommended = overrides.get('recommended', False)
                
                entries = topics if topics else [""]
                for topic in entries:
                    nc = NodeCourse(
                        node_id=node.id,
                        course_id=course_id,
                        requirement_id=requirement_id,
                        topic=topic,
                        comment=comment,
                        recommended=recommended
                    )
                    self.session.add(nc)
                    inserted[(course_id, topic)] = nc
                    stats['node_courses'] += 1
            
            # --- 第二轮：发现 combined courses ---
            for course_id in list(course_ids):
                course = self.session.query(Course).get(course_id)
                if not course:
                    continue
                
                overrides = course_overrides.get(course_id, {})
                topics = overrides.get('topics', [])
                entries = topics if topics else [""]
                
                for topic in entries:
                    combined_info = self._find_combined_courses(
                        course_id, topic, course.last_offered_semester
                    )
                    if not combined_info:
                        continue
                    
                    cg_id, combined_course_ids = combined_info
                    
                    # 给原课程设上 combined_group_id
                    key = (course_id, topic)
                    if key in inserted and inserted[key].combined_group_id is None:
                        inserted[key].combined_group_id = cg_id
                    
                    # 插入 combined courses
                    for combined_cid in combined_course_ids:
                        if combined_cid in excluded:
                            continue
                        
                        combined_key = (combined_cid, topic)
                        if combined_key in inserted:
                            # 已存在（可能是 query 直接匹配的）→ 补上 combined_group_id
                            if inserted[combined_key].combined_group_id is None:
                                inserted[combined_key].combined_group_id = cg_id
                            continue
                        
                        # 验证课程存在
                        combined_course = self.session.query(Course).get(combined_cid)
                        if not combined_course:
                            stats['courses_not_found'].append(combined_cid)
                            print(f"    ⚠️ Combined 课程不存在: {combined_cid}")
                            continue
                        
                        nc = NodeCourse(
                            node_id=node.id,
                            course_id=combined_cid,
                            requirement_id=requirement_id,
                            topic=topic,
                            combined_group_id=cg_id,
                        )
                        self.session.add(nc)
                        inserted[combined_key] = nc
                        stats['node_courses'] += 1
                        stats['combined_courses'] += 1
                        print(f"    + Combined: {combined_cid} (← {course_id}, cg={cg_id})")
        
        return node
    
    def _find_combined_courses(self, course_id, topic, last_offered_semester):
        """
        查找一门课的 combined courses
        
        逻辑：
        - topic="" 时：取 last_offered_semester 中该课程的所有 enroll group，
          找到它们的 combined_group，返回同组其他课程
        - topic!="" 时：取该课程 + 该 topic 的所有 enroll group，
          找到最近学期的那些，然后查 combined_group
        
        Args:
            course_id: 课程 ID
            topic: topic 限定（""表示不限）
            last_offered_semester: 课程最后开设的学期
        
        Returns:
            tuple(int, list[str]) | None: (combined_group_id, [其他课程ID列表])，
                                          无 combined 关系时返回 None
        """
        if not last_offered_semester:
            return None
        
        if topic == "":
            # 不限 topic：取 last_offered_semester 的所有 enroll group
            egs = (
                self.session.query(EnrollGroup)
                .filter(
                    EnrollGroup.course_id == course_id,
                    EnrollGroup.semester == last_offered_semester,
                    EnrollGroup.combined_group_id.isnot(None)
                )
                .all()
            )
        else:
            # 限定 topic：先找到该 course + topic 的所有 enroll group
            all_topic_egs = (
                self.session.query(EnrollGroup)
                .filter(
                    EnrollGroup.course_id == course_id,
                    EnrollGroup.topic == topic,
                    EnrollGroup.combined_group_id.isnot(None)
                )
                .all()
            )
            if not all_topic_egs:
                return None
            
            # 找最近学期
            latest_semester = max(
                (eg.semester for eg in all_topic_egs),
                key=lambda s: parse_semester(s)
            )
            egs = [eg for eg in all_topic_egs if eg.semester == latest_semester]
        
        if not egs:
            return None
        
        # 收集所有 combined_group_id
        cg_ids = set(eg.combined_group_id for eg in egs)
        
        # 查找同组的其他课程
        combined_course_ids = set()
        chosen_cg_id = None
        
        for cg_id in cg_ids:
            sibling_egs = (
                self.session.query(EnrollGroup.course_id)
                .filter(
                    EnrollGroup.combined_group_id == cg_id,
                    EnrollGroup.course_id != course_id
                )
                .distinct()
                .all()
            )
            if sibling_egs:
                if chosen_cg_id is None:
                    chosen_cg_id = cg_id
                for row in sibling_egs:
                    combined_course_ids.add(row[0])
        
        if not combined_course_ids:
            return None
        
        return (chosen_cg_id, sorted(combined_course_ids))
    
    def _resolve_query(self, query):
        """
        解析 YAML 中的 query，返回课程 ID 列表
        
        支持的 query 字段：
        - subject: 学科代码
        - level: 精确 level
        - min_level: 最低 level
        - max_level: 最高 level
        - included: 额外加入的课程 ID
        - excluded: 排除的课程 ID
        - course_overrides: {course_id: {topics, comment, recommended}}，由调用方处理，不影响本方法返回值
        
        Args:
            query: query 字典
        
        Returns:
            list: 排序后的课程 ID 列表
        """
        course_ids = set()
        
        # 显式包含的课程
        included = query.get('included', [])
        course_ids.update(included)
        
        # 从数据库查询
        if 'subject' in query:
            q = self.session.query(Course.id).filter(
                Course.subject == query['subject']
            )
            
            if 'level' in query:
                q = q.filter(Course.level == query['level'])
            if 'min_level' in query:
                q = q.filter(Course.level >= query['min_level'])
            if 'max_level' in query:
                q = q.filter(Course.level <= query['max_level'])
            
            results = q.all()
            course_ids.update(r[0] for r in results)
        
        # 排除
        excluded = set(query.get('excluded', []))
        course_ids -= excluded
        
        return sorted(course_ids)
    
    def _create_requirement_set(self, rs_data, program_id):
        """
        创建 RequirementSet 及其关联的 RequirementSetRequirements
        
        Args:
            rs_data: requirement_set YAML 数据
            program_id: 专业 ID
        """
        applies_to = rs_data.get('applies_to', {})
        
        requirement_set = RequirementSet(
            program_id=program_id,
            applies_to_entry_year=applies_to.get('entry_year'),
            applies_to_college_id=applies_to.get('college_id'),
            applies_to_major_id=applies_to.get('major_id'),
            applies_to_concentration_names=applies_to.get('concentration_names')
        )
        self.session.add(requirement_set)
        self.session.flush()
        
        # 创建关联记录
        requirement_ids = rs_data.get('requirement_ids', [])
        for idx, req_id in enumerate(requirement_ids):
            rsr = RequirementSetRequirement(
                requirement_set_id=requirement_set.id,
                requirement_id=req_id,
                position=idx
            )
            self.session.add(rsr)
    
    def _create_conflict_domain(self, domain_members, program_id):
        """
        创建一个 Conflict Domain 及其成员
        
        Args:
            domain_members: requirement ID 列表，如 ["arth1", "arth2", ...]
            program_id: 专业 ID
        """
        domain = RequirementDomain(program_id=program_id)
        self.session.add(domain)
        self.session.flush()
        
        for req_id in domain_members:
            membership = RequirementDomainMembership(
                domain_id=domain.id,
                requirement_id=req_id
            )
            self.session.add(membership)
