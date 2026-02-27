"""
ProgramSubject 数据模型
program 和 subject 的多对多关联表
"""
from sqlalchemy import Column, String, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class ProgramSubject(Base):
    """专业-学科关联表"""
    __tablename__ = 'program_subjects'

    program_id = Column(
        String(50),
        ForeignKey('programs.id', ondelete='CASCADE'),
        nullable=False
    )
    subject_id = Column(
        String(10),
        ForeignKey('subjects.value', ondelete='CASCADE'),
        nullable=False
    )

    # 关系
    program = relationship("Program", back_populates="program_subjects")
    subject = relationship("Subject")

    __table_args__ = (
        PrimaryKeyConstraint('program_id', 'subject_id'),
    )

    def __repr__(self):
        return f"<ProgramSubject {self.program_id} → {self.subject_id}>"
