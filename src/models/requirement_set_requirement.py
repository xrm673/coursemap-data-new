"""
RequirementSetRequirement 数据模型
RequirementSet 和 Requirement 的多对多关系
"""
from sqlalchemy import Column, String, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class RequirementSetRequirement(Base):
    """RequirementSet-Requirement 关联表"""
    __tablename__ = 'requirement_set_requirements'
    
    # 复合主键
    requirement_set_id = Column(
        Integer,
        ForeignKey('requirement_sets.id', ondelete='CASCADE'),
        nullable=False
    )
    requirement_id = Column(
        String(50),
        ForeignKey('requirements.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # 显示顺序
    position = Column(Integer, nullable=False)
    
    # 关系
    requirement_set = relationship("RequirementSet", back_populates="items")
    requirement = relationship("Requirement", back_populates="requirement_set_items")
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('requirement_set_id', 'requirement_id'),
    )
    
    def __repr__(self):
        return f"<RequirementSetRequirement set={self.requirement_set_id} req={self.requirement_id}>"
