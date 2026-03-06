#!/usr/bin/env python3
"""
用户删除脚本
通过 netid 从数据库中删除指定用户及其所有关联数据

使用方法：
  python scripts/delete_user.py --netid abc123
  python scripts/delete_user.py --netid abc123 --force   # 跳过确认步骤
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Database
from models.user import User


def parse_args():
    parser = argparse.ArgumentParser(
        description='通过 netid 删除用户',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/delete_user.py --netid abc123           # 删除用户（需确认）
  python scripts/delete_user.py --netid abc123 --force   # 跳过确认直接删除
        """
    )

    parser.add_argument(
        '--netid',
        type=str,
        required=True,
        help='要删除的用户 netid'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='跳过确认步骤，直接删除'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("用户删除工具")
    print("=" * 60)

    # 1. 连接数据库
    db = Database()
    if not db.test_connection():
        print("\n数据库连接失败，请检查 .env 配置")
        sys.exit(1)
    print()

    session = db.get_session()

    try:
        # 2. 查找用户
        user = session.query(User).filter(User.netid == args.netid).first()

        if user is None:
            print(f"✗ 未找到 netid 为 '{args.netid}' 的用户")
            sys.exit(1)

        # 3. 打印用户信息
        print("找到以下用户：")
        print(f"  netid      : {user.netid}")
        print(f"  姓名       : {user.first_name} {user.last_name}")
        print(f"  邮箱       : {user.email}")
        print(f"  学院       : {user.college_id}")
        print(f"  入学年份   : {user.entry_year}")
        print(f"  注册时间   : {user.created_at}")
        print()
        print("⚠️  删除该用户将同时清除其所有关联数据：")
        print("     user_program / user_courses / user_concentrations")
        print("     以及对应的 user_course_sections / user_course_requirements")
        print()

        # 4. 确认步骤
        if not args.force:
            confirm = input("确认删除？输入 y 继续，其他任意键取消：").strip().lower()
            if confirm != 'y':
                print("\n已取消，未作任何修改。")
                sys.exit(0)

        # 5. 执行删除
        session.delete(user)
        session.commit()
        print(f"\n✓ 用户 '{args.netid}' 已成功删除。")

    except Exception as e:
        session.rollback()
        print(f"\n✗ 删除失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        session.close()

    print("=" * 60)


if __name__ == "__main__":
    main()
