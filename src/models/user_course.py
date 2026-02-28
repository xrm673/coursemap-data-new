"""
UserCourse 数据模型
记录用户的课程记录（已上/计划中/收藏）

唯一性说明：
  - 数据库层：(user_id, course_id, semester, topic) 唯一约束，覆盖 semester/topic 均非 NULL 的情况
  - 应用层：插入 is_scheduled=False（收藏）记录前，需手动查重（因 NULL 列绕过数据库唯一约束）
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class UserCourse(Base):
    """用户课程记录表"""
    __tablename__ = 'user_courses'

    # 主键：自增整数
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    course_id = Column(String(20), ForeignKey('courses.id', ondelete='RESTRICT'), nullable=False, index=True)

    # 课程信息
    topic = Column(String(255), nullable=False)
    credits_received = Column(Float, nullable=True)
    semester = Column(String(10), nullable=True)

    # 状态：True = 已安排进课表（过去/现在/未来计划），False = 收藏
    is_scheduled = Column(Boolean, nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    user = relationship("User", back_populates="user_courses")
    course = relationship("Course", back_populates="user_courses")
    user_course_sections = relationship(
        "UserCourseSection",
        back_populates="user_course",
        cascade="all, delete-orphan"  # 删除 user_course 时级联删除关联的 section 记录
    )
    user_course_requirements = relationship(
        "UserCourseRequirement",
        back_populates="user_course",
        cascade="all, delete-orphan"  # 删除 user_course 时级联删除计入记录
    )

    # 唯一约束（仅覆盖 semester / topic 均非 NULL 的情况，NULL 情况需应用层保证）
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', 'semester', 'topic',
                         name='uq_user_course_semester_topic'),
    )

    def __repr__(self):
        status = "scheduled" if self.is_scheduled else "favorited"
        return f"<UserCourse user={self.user_id} course={self.course_id} [{status}]>"

    def __str__(self):
        semester_str = self.semester or "no semester"
        return f"{self.course_id} ({semester_str}) - {self.topic}"
