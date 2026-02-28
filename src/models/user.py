"""
User 数据模型
表示系统用户
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class User(Base):
    """用户表"""
    __tablename__ = 'users'

    # 主键：自增整数
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 账号信息
    netid = Column(String(15), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    # 个人信息
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    # 学院和入学年份
    college_id = Column(String(20), ForeignKey('colleges.id', ondelete='RESTRICT'), nullable=False)
    entry_year = Column(String(10), nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    college = relationship("College", back_populates="users")
    user_programs = relationship(
        "UserProgram",
        back_populates="user",
        cascade="all, delete-orphan"  # 删除用户时级联删除其专业记录
    )
    user_courses = relationship(
        "UserCourse",
        back_populates="user",
        cascade="all, delete-orphan"  # 删除用户时级联删除其课程记录
    )
    user_concentrations = relationship(
        "UserConcentration",
        back_populates="user",
        cascade="all, delete-orphan"  # 删除用户时级联删除其 concentration 记录
    )

    def __repr__(self):
        return f"<User {self.id}: {self.netid}>"

    def __str__(self):
        return f"{self.netid} - {self.first_name} {self.last_name}"
