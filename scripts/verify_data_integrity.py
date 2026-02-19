#!/usr/bin/env python3
"""
数据完整性检查脚本
对比 API 数据和数据库数据，检查导入是否完整
"""
import sys
import os
import argparse
from collections import defaultdict

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Database
from models import Course, EnrollGroup, Subject
from services.api_service import APIService
from sqlalchemy import func


class DataIntegrityChecker:
    """数据完整性检查器"""
    
    def __init__(self, semester):
        self.semester = semester
        self.api_service = APIService()
        db = Database()
        self.session = db.get_session()
        
        # API 数据 - 使用集合存储，方便对比
        self.api_subjects = []
        self.api_course_ids = defaultdict(set)  # subject -> {course_ids}
        self.api_course_details = defaultdict(dict)  # subject -> {course_id -> {title, ...}}
        self.api_eg_keys = defaultdict(set)  # subject -> {(course_id, first_section)}
        
        # 数据库数据 - 使用集合存储
        self.db_subjects = set()
        self.db_course_ids = defaultdict(set)  # subject -> {course_ids}
        self.db_eg_keys = defaultdict(set)  # subject -> {(course_id, first_section)}
        
        # 问题记录
        self.issues = {
            'missing_subjects': [],
            'course_mismatches': [],
            'eg_mismatches': [],
            'api_errors': []
        }
    
    def run(self, target_subjects=None):
        """
        运行完整性检查
        
        Args:
            target_subjects: 可选，只检查指定的 subjects
        """
        print(f"\n{'='*70}")
        print(f"数据完整性检查: {self.semester}")
        print(f"{'='*70}\n")
        
        # 1. 获取 API 数据
        print("步骤 1: 从 API 获取数据...")
        print("-" * 70)
        self._fetch_api_data(target_subjects)
        
        # 2. 获取数据库数据
        print("\n步骤 2: 从数据库查询数据...")
        print("-" * 70)
        self._fetch_db_data()
        
        # 3. 对比 Subject 层面
        print("\n步骤 3: 检查 Subject 层面...")
        print("-" * 70)
        self._check_subjects()
        
        # 4. 对比 Course 层面
        print("\n步骤 4: 检查 Course 层面...")
        print("-" * 70)
        self._check_courses()
        
        # 5. 对比 EnrollGroup 层面
        print("\n步骤 5: 检查 EnrollGroup 层面...")
        print("-" * 70)
        self._check_enroll_groups()
        
        # 6. 汇总报告
        print("\n步骤 6: 生成汇总报告...")
        print("-" * 70)
        self._generate_summary()
        
        self.session.close()
    
    def _fetch_api_data(self, target_subjects=None):
        """从 API 获取数据"""
        # 获取 subjects 列表
        subjects_data = self.api_service.fetch_subjects(self.semester)
        if not subjects_data:
            print("✗ 无法获取 subjects 数据")
            return
        
        self.api_subjects = [s['value'] for s in subjects_data]
        
        # 如果指定了 target_subjects，只检查这些
        if target_subjects:
            self.api_subjects = [s for s in self.api_subjects if s in target_subjects]
        
        print(f"从 API 获取到 {len(self.api_subjects)} 个 subjects")
        
        # 遍历每个 subject，获取课程数据
        for idx, subject in enumerate(self.api_subjects, 1):
            print(f"  [{idx}/{len(self.api_subjects)}] 获取 {subject}...", end=' ')
            
            try:
                classes_data = self.api_service.fetch_courses(self.semester, subject)
                
                if not classes_data:
                    print("0 门课程")
                    continue
                
                # 收集课程 ID 和 EG 信息
                for class_data in classes_data:
                    course_id = class_data['subject'] + class_data['catalogNbr']
                    
                    # 记录课程 ID
                    self.api_course_ids[subject].add(course_id)
                    
                    # 记录课程详情（用于报告）
                    self.api_course_details[subject][course_id] = {
                        'title': class_data.get('titleShort', ''),
                        'catalogNbr': class_data['catalogNbr']
                    }
                    
                    # 收集 EnrollGroup 信息：(course_id, first_section)
                    enroll_groups = class_data.get('enrollGroups', [])
                    for eg in enroll_groups:
                        class_sections = eg.get('classSections', [])
                        if class_sections:
                            first_section = class_sections[0].get('section')
                            if first_section:
                                self.api_eg_keys[subject].add((course_id, first_section))
                
                course_count = len(self.api_course_ids[subject])
                eg_count = len(self.api_eg_keys[subject])
                print(f"{course_count} 门课程, {eg_count} 个 EG")
                
            except Exception as e:
                print(f"✗ 错误: {e}")
                self.issues['api_errors'].append(f"{subject}: {e}")
        
        print(f"\nAPI 数据获取完成!")
        print(f"  Subjects: {len(self.api_subjects)}")
        print(f"  Courses: {sum(len(ids) for ids in self.api_course_ids.values())}")
        print(f"  EnrollGroups: {sum(len(keys) for keys in self.api_eg_keys.values())}")
    
    def _fetch_db_data(self):
        """从数据库查询数据"""
        # 查询该学期的所有 subjects（通过 EnrollGroup）
        subjects_query = self.session.query(Course.subject).join(
            EnrollGroup, EnrollGroup.course_id == Course.id
        ).filter(
            EnrollGroup.semester == self.semester
        ).distinct()
        
        self.db_subjects = {row[0] for row in subjects_query}
        
        # 查询该学期开设的所有课程 ID（通过 EnrollGroup）
        courses_query = self.session.query(
            Course.subject,
            Course.id
        ).join(
            EnrollGroup, EnrollGroup.course_id == Course.id
        ).filter(
            EnrollGroup.semester == self.semester
        ).distinct()
        
        for subject, course_id in courses_query:
            self.db_course_ids[subject].add(course_id)
        
        # 查询所有 EnrollGroup 的 (course_id, first_section) 组合
        eg_query = self.session.query(
            Course.subject,
            EnrollGroup.course_id,
            EnrollGroup.first_section_number
        ).join(
            EnrollGroup, EnrollGroup.course_id == Course.id
        ).filter(
            EnrollGroup.semester == self.semester
        )
        
        for subject, course_id, first_section in eg_query:
            self.db_eg_keys[subject].add((course_id, first_section))
        
        print(f"数据库数据查询完成!")
        print(f"  Subjects: {len(self.db_subjects)}")
        print(f"  Courses: {sum(len(ids) for ids in self.db_course_ids.values())}")
        print(f"  EnrollGroups: {sum(len(keys) for keys in self.db_eg_keys.values())}")
    
    def _check_subjects(self):
        """检查 Subject 层面"""
        print(f"\n{'Subject 层面对比':^70}")
        print("=" * 70)
        
        api_count = len(self.api_subjects)
        db_count = len(self.db_subjects)
        
        print(f"API Subjects:  {api_count}")
        print(f"DB Subjects:   {db_count}")
        print(f"差异:          {db_count - api_count:+d}")
        
        # 找出缺失的 subjects
        api_set = set(self.api_subjects)
        missing = api_set - self.db_subjects
        extra = self.db_subjects - api_set
        
        if missing:
            print(f"\n✗ 数据库中缺失的 Subjects ({len(missing)} 个):")
            for subject in sorted(missing):
                print(f"    - {subject}")
                self.issues['missing_subjects'].append(subject)
        
        if extra:
            print(f"\n⚠ 数据库中多出的 Subjects ({len(extra)} 个):")
            print("  (可能是其他学期的课程)")
            for subject in sorted(extra):
                print(f"    - {subject}")
        
        if not missing and not extra:
            print("\n✓ Subject 层面完全匹配!")
    
    def _check_courses(self):
        """检查 Course 层面"""
        print(f"\n{'Course 层面对比':^70}")
        print("=" * 70)
        
        # 表头
        print(f"{'Subject':<12} {'API':>6} {'DB':>6} {'差异':>6}  {'状态'}")
        print("-" * 70)
        
        matched = 0
        mismatched = 0
        
        # 遍历所有 API subjects
        for subject in sorted(self.api_subjects):
            api_ids = self.api_course_ids[subject]
            db_ids = self.db_course_ids.get(subject, set())
            
            api_count = len(api_ids)
            db_count = len(db_ids)
            diff = db_count - api_count
            
            if diff == 0 and api_ids == db_ids:
                status = "✓"
                matched += 1
            else:
                status = "✗"
                mismatched += 1
                
                # 找出缺失和多余的课程
                missing_ids = api_ids - db_ids  # API 有但 DB 没有
                extra_ids = db_ids - api_ids    # DB 有但 API 没有
                
                self.issues['course_mismatches'].append({
                    'subject': subject,
                    'api_count': api_count,
                    'db_count': db_count,
                    'diff': diff,
                    'missing_ids': missing_ids,
                    'extra_ids': extra_ids
                })
            
            print(f"{subject:<12} {api_count:>6} {db_count:>6} {diff:>+6}  {status}")
        
        # 统计
        total = len(self.api_subjects)
        print("-" * 70)
        print(f"总计: 匹配 {matched}/{total}, 不匹配 {mismatched}/{total}")
        
        if mismatched == 0:
            print("\n✓ Course 层面完全匹配!")
    
    def _check_enroll_groups(self):
        """检查 EnrollGroup 层面"""
        print(f"\n{'EnrollGroup 层面对比':^70}")
        print("=" * 70)
        
        # 表头
        print(f"{'Subject':<12} {'API':>6} {'DB':>6} {'差异':>6}  {'状态'}")
        print("-" * 70)
        
        matched = 0
        mismatched = 0
        
        # 遍历所有 API subjects
        for subject in sorted(self.api_subjects):
            api_keys = self.api_eg_keys[subject]
            db_keys = self.db_eg_keys.get(subject, set())
            
            api_count = len(api_keys)
            db_count = len(db_keys)
            diff = db_count - api_count
            
            if diff == 0 and api_keys == db_keys:
                status = "✓"
                matched += 1
            else:
                status = "✗"
                mismatched += 1
                
                # 找出缺失和多余的 EG
                missing_keys = api_keys - db_keys  # API 有但 DB 没有
                extra_keys = db_keys - api_keys    # DB 有但 API 没有
                
                self.issues['eg_mismatches'].append({
                    'subject': subject,
                    'api_count': api_count,
                    'db_count': db_count,
                    'diff': diff,
                    'missing_keys': missing_keys,
                    'extra_keys': extra_keys
                })
            
            print(f"{subject:<12} {api_count:>6} {db_count:>6} {diff:>+6}  {status}")
        
        # 统计
        total = len(self.api_subjects)
        print("-" * 70)
        print(f"总计: 匹配 {matched}/{total}, 不匹配 {mismatched}/{total}")
        
        if mismatched == 0:
            print("\n✓ EnrollGroup 层面完全匹配!")
    
    def _generate_summary(self):
        """生成汇总报告"""
        print(f"\n{'='*70}")
        print(f"{'最终汇总报告':^70}")
        print(f"{'='*70}\n")
        
        has_issues = False
        
        # 1. Subject 层面问题
        if self.issues['missing_subjects']:
            has_issues = True
            print(f"【问题 1】缺失的 Subjects ({len(self.issues['missing_subjects'])} 个)")
            print("-" * 70)
            for subject in self.issues['missing_subjects']:
                api_count = len(self.api_course_ids[subject])
                print(f"  • {subject}: API 有 {api_count} 门课程，但数据库中一门都没有")
            print()
        
        # 2. Course 层面问题
        if self.issues['course_mismatches']:
            has_issues = True
            print(f"【问题 2】Course 数量不匹配 ({len(self.issues['course_mismatches'])} 个 subjects)")
            print("-" * 70)
            for issue in self.issues['course_mismatches']:
                subject = issue['subject']
                print(f"  • {subject}: API {issue['api_count']} 门 vs DB {issue['db_count']} 门 (差异: {issue['diff']:+d})")
                
                # 显示缺失的课程
                if issue['missing_ids']:
                    print(f"    缺失的课程 (API 有但 DB 没有):")
                    for course_id in sorted(issue['missing_ids'])[:10]:
                        title = self.api_course_details[subject][course_id]['title']
                        print(f"      - {course_id}: {title}")
                    if len(issue['missing_ids']) > 10:
                        print(f"      ... 还有 {len(issue['missing_ids']) - 10} 门课程")
                
                # 显示多余的课程
                if issue['extra_ids']:
                    print(f"    多余的课程 (DB 有但 API 没有):")
                    for course_id in sorted(issue['extra_ids'])[:10]:
                        print(f"      - {course_id}")
                    if len(issue['extra_ids']) > 10:
                        print(f"      ... 还有 {len(issue['extra_ids']) - 10} 门课程")
            print()
        
        # 3. EnrollGroup 层面问题
        if self.issues['eg_mismatches']:
            has_issues = True
            print(f"【问题 3】EnrollGroup 数量不匹配 ({len(self.issues['eg_mismatches'])} 个 subjects)")
            print("-" * 70)
            for issue in self.issues['eg_mismatches']:
                subject = issue['subject']
                diff = issue['diff']
                print(f"  • {subject}: API {issue['api_count']} 个 vs DB {issue['db_count']} 个 (差异: {diff:+d})")
                
                # 显示缺失的 EG
                if issue['missing_keys']:
                    print(f"    缺失的 EG (API 有但 DB 没有):")
                    for course_id, section in sorted(issue['missing_keys'])[:10]:
                        print(f"      - {course_id} section {section}")
                    if len(issue['missing_keys']) > 10:
                        print(f"      ... 还有 {len(issue['missing_keys']) - 10} 个 EG")
                
                # 显示多余的 EG
                if issue['extra_keys']:
                    print(f"    多余的 EG (DB 有但 API 没有):")
                    for course_id, section in sorted(issue['extra_keys'])[:10]:
                        print(f"      - {course_id} section {section}")
                    if len(issue['extra_keys']) > 10:
                        print(f"      ... 还有 {len(issue['extra_keys']) - 10} 个 EG")
            print()
        
        # 4. API 错误
        if self.issues['api_errors']:
            has_issues = True
            print(f"【问题 4】API 请求错误 ({len(self.issues['api_errors'])} 个)")
            print("-" * 70)
            for error in self.issues['api_errors']:
                print(f"  • {error}")
            print()
        
        # 最终结论
        if not has_issues:
            print("=" * 70)
            print(f"{'✓ 所有数据完全匹配！':^70}")
            print("=" * 70)
        else:
            print("=" * 70)
            print(f"{'✗ 发现数据不一致，请检查上述问题':^70}")
            print("=" * 70)
            
            # 建议
            print("\n【诊断建议】")
            print("-" * 70)
            if self.issues['missing_subjects']:
                print("  1. Subject 外键约束: 某些 subjects 可能不在 subjects 表中")
                print("     → 建议: 在导入课程前确保 subject 已存在")
            if self.issues['course_mismatches']:
                print("  2. Course 导入失败: 某些课程可能因为数据异常导致导入失败")
                print("     → 建议: 检查日志中的错误信息")
            if self.issues['eg_mismatches']:
                print("  3. EnrollGroup 导入失败: 某些注册组可能因为约束冲突导致导入失败")
                print("     → 建议: 检查 unique constraint 是否有冲突")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='检查数据库数据与 API 数据的完整性'
    )
    parser.add_argument(
        '--semester',
        type=str,
        required=True,
        help='学期代码 (如 FA25, SP26)'
    )
    parser.add_argument(
        '--subjects',
        type=str,
        nargs='+',
        help='可选: 只检查指定的 subjects (如 CS MATH)'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    checker = DataIntegrityChecker(args.semester)
    checker.run(target_subjects=args.subjects)


if __name__ == "__main__":
    main()
