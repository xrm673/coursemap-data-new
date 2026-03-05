"""
RequirementNode 数据模型
表示 requirement 树中的节点
节点分两种类型：SELECT（有子节点）和 COURSE_SET（有课程列表）
"""
from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from . import Base


class RequirementNode(Base):
    """Requirement 树节点表"""
    __tablename__ = 'requirement_nodes'
    
    # 主键：自动生成，如 "arth1_root", "arth1_1"
    id = Column(String(50), primary_key=True)
    
    # 外键：所属的 requirement
    requirement_id = Column(
        String(50),
        ForeignKey('requirements.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # 节点信息
    type = Column(String(20), nullable=False)  # "SELECT" / "COURSE_SET"
    title = Column(String(255), nullable=True)
    rule = Column(JSON, nullable=False)  # 完成规则，如 {"required_children_count": 3} 或 {"required_units_count": 1, "units_type": "COURSE"}
    
    # 关系
    requirement = relationship(
        "Requirement",
        back_populates="nodes",
        foreign_keys=[requirement_id]
    )
    
    # SELECT 节点的子节点关系
    children = relationship(
        "NodeChild",
        back_populates="parent_node",
        foreign_keys="NodeChild.parent_node_id",
        cascade="all, delete-orphan"
    )
    
    # COURSE_SET 节点的课程列表
    courses = relationship(
        "NodeCourse",
        back_populates="node",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<RequirementNode {self.id}: {self.type} rule={self.rule}>"
    
    def __str__(self):
        title_str = f" '{self.title}'" if self.title else ""
        return f"{self.type}{title_str} (rule={self.rule})"
