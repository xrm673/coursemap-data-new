"""
RequirementDomainMembership 数据模型
RequirementDomain 和 Requirement 的多对多关系
"""
from sqlalchemy import Column, String, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class RequirementDomainMembership(Base):
    """Requirement-Domain 关联表"""
    __tablename__ = 'requirement_domain_memberships'
    
    # 复合主键
    domain_id = Column(
        Integer,
        ForeignKey('requirement_domains.id', ondelete='CASCADE'),
        nullable=False
    )
    requirement_id = Column(
        String(50),
        ForeignKey('requirements.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # 关系
    domain = relationship("RequirementDomain", back_populates="memberships")
    requirement = relationship("Requirement", back_populates="domain_memberships")
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('domain_id', 'requirement_id'),
    )
    
    def __repr__(self):
        return f"<RequirementDomainMembership domain={self.domain_id} req={self.requirement_id}>"
