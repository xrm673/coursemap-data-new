"""
Requirement 数据模型
表示一个专业的某个具体要求（如 Core、Electives 等）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from . import Base



class Requirement(Base):
    """专业要求表"""
    __tablename__ = 'requirements'
    
    # 主键
    id = Column(String(50), primary_key=True)  # "arth1"
    
    # 外键：所属专业
    program_id = Column(String(20), ForeignKey('programs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 基本信息
    name = Column(String(255), nullable=False)  # "Core"
    ui_type = Column(String(20), nullable=False)  # "GROUP" / "LIST"
    description = Column(JSON, nullable=True)  # ["Take at least...", ...]
    
    # 外键：所属 concentration（可选，NULL 表示适用所有学生）
    concentration_id = Column(
        Integer,
        ForeignKey('program_concentrations.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )

    # 树的根节点（circular FK with nodes）
    root_node_id = Column(
        String(50),
        ForeignKey('requirement_nodes.id', use_alter=True, ondelete='SET NULL'),
        nullable=True
    )
    
    # 关系
    program = relationship("Program", back_populates="requirements")
    concentration = relationship("ProgramConcentration", back_populates="requirements")
    
    root_node = relationship(
        "RequirementNode",
        foreign_keys=[root_node_id],
        post_update=True  # 处理 circular FK
    )
    
    nodes = relationship(
        "RequirementNode",
        back_populates="requirement",
        foreign_keys="RequirementNode.requirement_id",
        cascade="all, delete-orphan"
    )
    
    requirement_set_items = relationship(
        "RequirementSetRequirement",
        back_populates="requirement",
        passive_deletes=True  # 让 DB 级别的 ondelete='CASCADE' 处理
    )
    
    domain_memberships = relationship(
        "RequirementDomainMembership",
        back_populates="requirement",
        passive_deletes=True
    )
    user_course_requirements = relationship(
        "UserCourseRequirement",
        back_populates="requirement",
        passive_deletes=True  # 由 DB 级别 ondelete='CASCADE' 处理
    )
    
    def __repr__(self):
        return f"<Requirement {self.id}: {self.name}>"
    
    def __str__(self):
        return f"{self.id} - {self.name} ({self.ui_type})"
