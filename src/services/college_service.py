"""
College 业务逻辑服务
负责从 YAML 文件导入学院数据
"""
import json
import os
import yaml
from jsonschema import Draft7Validator
from models import College, CollegeProgram, CollegeSubject


_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', '..', 'data', 'colleges', 'schema.json'
)

_SCHEMA = None


def _load_schema():
    path = os.path.normpath(_SCHEMA_PATH)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class CollegeService:
    """学院数据导入服务"""

    @staticmethod
    def validate_yaml(yaml_path):
        """
        校验一个 college YAML 文件是否符合 schema。

        Args:
            yaml_path: YAML 文件路径

        Returns:
            list[str]: 校验错误列表，空列表表示通过
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
        Args:
            session: SQLAlchemy 数据库会话
        """
        self.session = session

    def import_from_yaml(self, yaml_path):
        """
        从 YAML 文件导入学院数据（幂等）

        流程：
        1. 校验 schema
        2. 删除该学院的现有数据（clean re-import）
        3. 创建 College
        4. 创建 college_programs 关联
        5. 创建 college_subjects 关联
        6. 提交

        Args:
            yaml_path: YAML 文件路径

        Returns:
            dict: 统计信息
        """
        # 校验 schema
        errors = CollegeService.validate_yaml(yaml_path)
        if errors:
            error_msg = '\n'.join(errors)
            raise ValueError(f"YAML 文件校验失败：{yaml_path}\n{error_msg}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        college_data = data['college']
        college_id = college_data['id']
        programs = data.get('programs', [])
        subjects = data.get('subjects', [])

        print(f"\n{'='*60}")
        print(f"导入学院: {college_id} - {college_data['name']}")
        print(f"{'='*60}")

        stats = {
            'college_id': college_id,
            'programs': 0,
            'subjects': 0,
        }

        # 1. 删除现有数据
        self._delete_college(college_id)

        # 2. 创建 College
        college = College(id=college_id, name=college_data['name'])
        self.session.add(college)
        self.session.flush()
        print(f"✓ 创建 College: {college}")

        # 3. 创建 college_programs
        for program_id in programs:
            self.session.add(CollegeProgram(
                college_id=college_id,
                program_id=program_id
            ))
            stats['programs'] += 1
        self.session.flush()
        print(f"✓ 关联 {stats['programs']} 个 Programs")

        # 4. 创建 college_subjects
        for subject_id in subjects:
            self.session.add(CollegeSubject(
                college_id=college_id,
                subject_id=subject_id
            ))
            stats['subjects'] += 1
        self.session.flush()
        print(f"✓ 关联 {stats['subjects']} 个 Subjects")

        # 5. 提交
        try:
            self.session.commit()
            print(f"\n{'='*60}")
            print(f"✓ 导入完成！")
            print(f"{'='*60}")
            print(f"  Programs: {stats['programs']}")
            print(f"  Subjects: {stats['subjects']}")
            print(f"{'='*60}\n")
            return stats
        except Exception as e:
            self.session.rollback()
            print(f"✗ 提交失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _delete_college(self, college_id):
        """
        删除某个学院的所有数据（用于 clean re-import）
        """
        college = self.session.query(College).get(college_id)
        if not college:
            print(f"  学院 {college_id} 不存在，跳过删除")
            return
        self.session.delete(college)
        self.session.flush()
        print(f"  已删除旧数据: {college_id}")
