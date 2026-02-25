"""
RequirementDomain 数据模型
表示一组互相冲突的 requirement 所属的 domain
同一 domain 内的 requirement 不能用同一门课重复满足
"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from . import Base


class RequirementDomain(Base):
    """Requirement 冲突域表"""
    __tablename__ = 'requirement_domains'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 外键：所属专业
    program_id = Column(String(20), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 关系
    program = relationship("Program", back_populates="requirement_domains")
    memberships = relationship(
        "RequirementDomainMembership",
        back_populates="domain",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<RequirementDomain {self.id} for {self.program_id}>"
