#!/usr/bin/env python3
"""
专业要求数据导入脚本
从 YAML 文件读取专业要求并导入数据库

使用方法：
  python scripts/import_programs.py --programs ARTH CS
  python scripts/import_programs.py --all
  python scripts/import_programs.py --validate           # 校验所有 YAML 文件
  python scripts/import_programs.py --validate ARTH CS   # 校验指定文件
"""
import sys
import os
import argparse
import glob

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Database
from services import ProgramService

# YAML 文件目录
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'programs')


def find_yaml_files(program_ids=None):
    """
    查找 YAML 文件
    
    Args:
        program_ids: 指定的专业 ID 列表，如 ["ARTH", "CS"]。
                     None 表示查找所有。
    
    Returns:
        list: [(program_id, yaml_path), ...]
    """
    if program_ids:
        # 查找指定的 YAML 文件
        files = []
        for pid in program_ids:
            yaml_path = os.path.join(DATA_DIR, f"{pid.lower()}.yml")
            if os.path.exists(yaml_path):
                files.append((pid, yaml_path))
            else:
                print(f"⚠️ 未找到 YAML 文件: {yaml_path}")
        return files
    else:
        # 查找所有 YAML 文件
        pattern = os.path.join(DATA_DIR, '*.yml')
        files = []
        for yaml_path in sorted(glob.glob(pattern)):
            filename = os.path.basename(yaml_path)
            pid = os.path.splitext(filename)[0].upper()
            files.append((pid, yaml_path))
        return files


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='导入专业要求数据（从 YAML 文件）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/import_programs.py --programs ARTH          # 导入 ARTH
  python scripts/import_programs.py --programs ARTH CS MATH  # 导入多个专业
  python scripts/import_programs.py --all                    # 导入所有 YAML 文件
  python scripts/import_programs.py --validate               # 校验所有 YAML 文件（不需要数据库）
  python scripts/import_programs.py --validate ARTH          # 校验指定文件
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--programs',
        nargs='+',
        metavar='ID',
        help='指定要导入的专业 ID（如 ARTH CS MATH）'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='导入 data/programs/ 目录下的所有 YAML 文件'
    )
    group.add_argument(
        '--validate',
        nargs='*',
        metavar='ID',
        help='仅校验 YAML 文件格式，不写入数据库。不加 ID 则校验所有文件。'
    )

    return parser.parse_args()


def run_validate(program_ids):
    """
    仅做 schema 校验，不连接数据库
    
    Args:
        program_ids: 专业 ID 列表，None 或 [] 表示全部
    """
    print("=" * 60)
    print("YAML 文件 Schema 校验")
    print("=" * 60)

    yaml_files = find_yaml_files(program_ids if program_ids else None)
    if not yaml_files:
        print("没有找到任何 YAML 文件")
        return

    print(f"校验 {len(yaml_files)} 个文件:\n")

    all_passed = True
    for pid, yaml_path in yaml_files:
        errors = ProgramService.validate_yaml(yaml_path)
        if errors:
            all_passed = False
            print(f"✗ {pid} ({os.path.basename(yaml_path)})")
            for msg in errors:
                print(msg)
        else:
            print(f"✓ {pid} ({os.path.basename(yaml_path)})")

    print()
    if all_passed:
        print("所有文件校验通过 ✓")
    else:
        print("部分文件存在错误，请修复后再导入 ✗")
        sys.exit(1)


def main():
    """主函数"""
    args = parse_args()

    # --validate 模式：不需要数据库
    if args.validate is not None:
        run_validate(args.validate)
        return

    print("=" * 60)
    print("专业要求数据导入")
    print("=" * 60)
    
    # 1. 查找 YAML 文件
    if args.all:
        yaml_files = find_yaml_files()
        print(f"模式: 导入全部")
    else:
        yaml_files = find_yaml_files(args.programs)
        print(f"模式: 导入指定专业 {args.programs}")
    
    if not yaml_files:
        print("\n没有找到任何 YAML 文件")
        return
    
    print(f"找到 {len(yaml_files)} 个 YAML 文件:")
    for pid, path in yaml_files:
        print(f"  • {pid}: {path}")
    print()
    
    # 2. 初始化数据库
    print("初始化数据库连接...")
    db = Database()
    if not db.test_connection():
        print("\n数据库连接失败，请检查 .env 配置")
        return
    
    # 确保表存在
    if not db.create_tables():
        print("\n数据表创建失败，程序终止")
        return
    print()
    
    # 3. 导入每个专业
    session = db.get_session()
    service = ProgramService(session)
    
    success_count = 0
    fail_count = 0
    
    for idx, (pid, yaml_path) in enumerate(yaml_files, 1):
        print(f"\n[{idx}/{len(yaml_files)}] 导入 {pid}")
        print("-" * 60)
        
        try:
            stats = service.import_from_yaml(yaml_path)
            success_count += 1
        except Exception as e:
            print(f"✗ 导入 {pid} 失败: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
    
    # 4. 关闭会话
    session.close()
    
    # 5. 汇总
    print("\n" + "=" * 60)
    print(f"导入完成！成功: {success_count}, 失败: {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
