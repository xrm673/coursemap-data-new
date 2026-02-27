"""
Program 数据模型
表示专业/辅修（如 History of Art Major）
"""
from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.orm import relationship
from . import Base


class Program(Base):
    """专业/辅修表"""
    __tablename__ = 'programs'
    
    # 主键：专业代码
    id = Column(String(20), primary_key=True)  # "ARTH"
    
    # 基本信息
    name = Column(String(255), nullable=False)  # "History of Art"
    type = Column(String(10), nullable=False)   # "major" / "minor"
    
    # 条件依赖标记
    year_dependent = Column(Boolean, default=False, nullable=False)
    major_dependent = Column(Boolean, default=False, nullable=False)
    college_dependent = Column(Boolean, default=False, nullable=False)
    concentration_dependent = Column(Boolean, default=False, nullable=False)
    
    # JSON 字段
    onboarding_courses = Column(JSON, nullable=True)  # ["ARTH1100", "ARTH2000", ...]
    
    # 关系
    requirement_sets = relationship(
        "RequirementSet",
        back_populates="program",
        cascade="all, delete-orphan"
    )
    requirements = relationship(
        "Requirement",
        back_populates="program",
        cascade="all, delete-orphan"
    )
    requirement_domains = relationship(
        "RequirementDomain",
        back_populates="program",
        cascade="all, delete-orphan"
    )
    college_programs = relationship(
        "CollegeProgram",
        back_populates="program",
        cascade="all, delete-orphan"
    )
    program_subjects = relationship(
        "ProgramSubject",
        back_populates="program",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Program {self.id}: {self.name} ({self.type})>"
    
    def __str__(self):
        return f"{self.id} - {self.name} ({self.type})"
