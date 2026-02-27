"""
UserCourseSection 数据模型
user_courses 与 class_sections 的多对多关联表
"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from . import Base


class UserCourseSection(Base):
    """用户课程-Section 关联表"""
    __tablename__ = 'user_courses_section'

    # 复合主键
    user_course_id = Column(
        Integer,
        ForeignKey('user_courses.id', ondelete='CASCADE'),
        primary_key=True
    )
    class_section_id = Column(
        Integer,
        ForeignKey('class_sections.id', ondelete='CASCADE'),
        primary_key=True
    )

    # 关系
    user_course = relationship("UserCourse", back_populates="user_course_sections")
    class_section = relationship("ClassSection", back_populates="user_course_sections")

    def __repr__(self):
        return f"<UserCourseSection user_course={self.user_course_id} section={self.class_section_id}>"
