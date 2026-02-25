"""
Program 业务逻辑服务
负责从 YAML 文件导入专业要求数据
"""
import yaml
from models import (
    Course, Program, Requirement, RequirementSet, RequirementSetRequirement,
    RequirementDomain, RequirementDomainMembership,
    RequirementNode, NodeChild, NodeCourse
)


class ProgramService:
    """专业要求导入服务"""
    
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
        
        # 7. 创建 RequirementDomains
        conflict_domains_data = program_data.get('conflict_domains', [])
        for domain_members in conflict_domains_data:
            self._create_conflict_domain(domain_members, program_id)
            stats['domains'] += 1
        
        self.session.flush()
        print(f"✓ 创建 {stats['domains']} 个 Conflict Domains")
        
        # 8. 提交
        try:
            self.session.commit()
            print(f"\n{'='*60}")
            print(f"✓ 导入完成！")
            print(f"{'='*60}")
            print(f"  Requirements: {stats['requirements']}")
            print(f"  Nodes: {stats['nodes']}")
            print(f"  Node-Course 关联: {stats['node_courses']}")
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
            
            for course_id in course_ids:
                # 验证课程存在
                course = self.session.query(Course).get(course_id)
                if not course:
                    stats['courses_not_found'].append(course_id)
                    print(f"    ⚠️ 课程不存在: {course_id}")
                    continue
                
                node_course = NodeCourse(
                    node_id=node.id,
                    course_id=course_id
                )
                self.session.add(node_course)
                stats['node_courses'] += 1
        
        return node
    
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
