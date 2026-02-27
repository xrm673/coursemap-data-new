"""
College 数据模型
"""
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from . import Base


class College(Base):
    """学院表"""
    __tablename__ = 'colleges'

    id = Column(String(20), primary_key=True)
    name = Column(String(255), nullable=False)

    # 关系
    college_programs = relationship(
        "CollegeProgram",
        back_populates="college",
        cascade="all, delete-orphan"
    )
    college_subjects = relationship(
        "CollegeSubject",
        back_populates="college",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<College {self.id}: {self.name}>"
