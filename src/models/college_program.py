"""
CollegeProgram 数据模型
college 和 program 的多对多关联表
"""
from sqlalchemy import Column, String, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class CollegeProgram(Base):
    """学院-专业关联表"""
    __tablename__ = 'college_programs'

    college_id = Column(
        String(20),
        ForeignKey('colleges.id', ondelete='CASCADE'),
        nullable=False
    )
    program_id = Column(
        String(50),
        ForeignKey('programs.id', ondelete='CASCADE'),
        nullable=False
    )

    # 关系
    college = relationship("College", back_populates="college_programs")
    program = relationship("Program", back_populates="college_programs")

    __table_args__ = (
        PrimaryKeyConstraint('college_id', 'program_id'),
    )

    def __repr__(self):
        return f"<CollegeProgram {self.college_id} → {self.program_id}>"
