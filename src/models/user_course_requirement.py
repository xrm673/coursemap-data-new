"""
UserCourseRequirement 数据模型
记录用户的某门课被计入了哪个 requirement

冲突域说明：
  同一 conflict domain 内，一门 user_course 只能出现在一个 requirement 中。
  该约束由应用层在写入前检查 RequirementDomain / RequirementDomainMembership 实现。
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from . import Base


class UserCourseRequirement(Base):
    """用户课程-Requirement 计入记录表"""
    __tablename__ = 'user_course_requirements'

    # 复合主键
    user_course_id = Column(
        Integer,
        ForeignKey('user_courses.id', ondelete='CASCADE'),
        primary_key=True
    )
    requirement_id = Column(
        String(50),
        ForeignKey('requirements.id', ondelete='CASCADE'),
        primary_key=True
    )

    # 关系
    user_course = relationship("UserCourse", back_populates="user_course_requirements")
    requirement = relationship("Requirement", back_populates="user_course_requirements")

    # 索引：按 requirement 查找所有已计入该 requirement 的课
    __table_args__ = (
        Index('ix_user_course_requirement_requirement_id', 'requirement_id'),
    )

    def __repr__(self):
        return f"<UserCourseRequirement user_course={self.user_course_id} requirement={self.requirement_id}>"
