"""
RequirementSet 数据模型
表示一组适用条件下的 requirement 集合
"""
from sqlalchemy import Column, String, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from . import Base


class RequirementSet(Base):
    """Requirement 集合表"""
    __tablename__ = 'requirement_sets'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外键：所属专业
    program_id = Column(String(20), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 适用条件（全部可选，NULL 表示不限制）
    applies_to_entry_year = Column(String(10), nullable=True)
    applies_to_college_id = Column(String(10), nullable=True)
    applies_to_major_id = Column(String(20), nullable=True)
    applies_to_concentration_names = Column(JSON, nullable=True)  # ["Theory", "Systems"]
    
    # 关系
    program = relationship("Program", back_populates="requirement_sets")
    items = relationship(
        "RequirementSetRequirement",
        back_populates="requirement_set",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<RequirementSet {self.id} for {self.program_id}>"
