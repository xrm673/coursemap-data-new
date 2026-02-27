"""
CollegeSubject 数据模型
college 和 subject 的多对多关联表
"""
from sqlalchemy import Column, String, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class CollegeSubject(Base):
    """学院-学科关联表"""
    __tablename__ = 'college_subjects'

    college_id = Column(
        String(20),
        ForeignKey('colleges.id', ondelete='CASCADE'),
        nullable=False
    )
    subject_id = Column(
        String(10),
        ForeignKey('subjects.value', ondelete='CASCADE'),
        nullable=False
    )

    # 关系
    college = relationship("College", back_populates="college_subjects")
    subject = relationship("Subject")

    __table_args__ = (
        PrimaryKeyConstraint('college_id', 'subject_id'),
    )

    def __repr__(self):
        return f"<CollegeSubject {self.college_id} → {self.subject_id}>"
