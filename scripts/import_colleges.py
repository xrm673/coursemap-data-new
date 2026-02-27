#!/usr/bin/env python3
"""
学院数据导入脚本
从 YAML 文件读取学院信息并导入数据库

使用方法：
  python scripts/import_colleges.py --colleges CAS EN
  python scripts/import_colleges.py --all
  python scripts/import_colleges.py --validate
  python scripts/import_colleges.py --validate CAS
"""
import sys
import os
import argparse
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Database
from services import CollegeService

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'colleges')


def find_yaml_files(college_ids=None):
    """
    查找 YAML 文件

    Args:
        college_ids: 指定的学院 ID 列表，如 ["CAS", "EN"]。
                     None 表示查找所有。

    Returns:
        list: [(college_id, yaml_path), ...]
    """
    if college_ids:
        files = []
        for cid in college_ids:
            yaml_path = os.path.join(DATA_DIR, f"{cid.lower()}.yml")
            if os.path.exists(yaml_path):
                files.append((cid, yaml_path))
            else:
                print(f"⚠️ 未找到 YAML 文件: {yaml_path}")
        return files
    else:
        pattern = os.path.join(DATA_DIR, '*.yml')
        files = []
        for yaml_path in sorted(glob.glob(pattern)):
            filename = os.path.basename(yaml_path)
            if filename == 'schema.json':
                continue
            cid = os.path.splitext(filename)[0].upper()
            files.append((cid, yaml_path))
        return files


def parse_args():
    parser = argparse.ArgumentParser(
        description='导入学院数据（从 YAML 文件）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/import_colleges.py --colleges CAS          # 导入 CAS
  python scripts/import_colleges.py --colleges CAS EN       # 导入多个学院
  python scripts/import_colleges.py --all                   # 导入所有 YAML 文件
  python scripts/import_colleges.py --validate              # 校验所有 YAML 文件（不需要数据库）
  python scripts/import_colleges.py --validate CAS          # 校验指定文件
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--colleges',
        nargs='+',
        metavar='ID',
        help='指定要导入的学院 ID（如 CAS EN）'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='导入 data/colleges/ 目录下的所有 YAML 文件'
    )
    group.add_argument(
        '--validate',
        nargs='*',
        metavar='ID',
        help='仅校验 YAML 文件格式，不写入数据库。不加 ID 则校验所有文件。'
    )

    return parser.parse_args()


def run_validate(college_ids):
    print("=" * 60)
    print("YAML 文件 Schema 校验")
    print("=" * 60)

    yaml_files = find_yaml_files(college_ids if college_ids else None)
    if not yaml_files:
        print("没有找到任何 YAML 文件")
        return

    print(f"校验 {len(yaml_files)} 个文件:\n")

    all_passed = True
    for cid, yaml_path in yaml_files:
        errors = CollegeService.validate_yaml(yaml_path)
        if errors:
            all_passed = False
            print(f"✗ {cid} ({os.path.basename(yaml_path)})")
            for msg in errors:
                print(msg)
        else:
            print(f"✓ {cid} ({os.path.basename(yaml_path)})")

    print()
    if all_passed:
        print("所有文件校验通过 ✓")
    else:
        print("部分文件存在错误，请修复后再导入 ✗")
        sys.exit(1)


def main():
    args = parse_args()

    if args.validate is not None:
        run_validate(args.validate)
        return

    print("=" * 60)
    print("学院数据导入")
    print("=" * 60)

    if args.all:
        yaml_files = find_yaml_files()
        print(f"模式: 导入全部")
    else:
        yaml_files = find_yaml_files(args.colleges)
        print(f"模式: 导入指定学院 {args.colleges}")

    if not yaml_files:
        print("\n没有找到任何 YAML 文件")
        return

    print(f"找到 {len(yaml_files)} 个 YAML 文件:")
    for cid, path in yaml_files:
        print(f"  • {cid}: {path}")
    print()

    print("初始化数据库连接...")
    db = Database()
    if not db.test_connection():
        print("\n数据库连接失败，请检查 .env 配置")
        return

    if not db.create_tables():
        print("\n数据表创建失败，程序终止")
        return
    print()

    session = db.get_session()
    service = CollegeService(session)

    success_count = 0
    fail_count = 0

    for idx, (cid, yaml_path) in enumerate(yaml_files, 1):
        print(f"\n[{idx}/{len(yaml_files)}] 导入 {cid}")
        print("-" * 60)
        try:
            service.import_from_yaml(yaml_path)
            success_count += 1
        except Exception as e:
            print(f"✗ 导入 {cid} 失败: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1

    session.close()

    print("\n" + "=" * 60)
    print(f"导入完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
