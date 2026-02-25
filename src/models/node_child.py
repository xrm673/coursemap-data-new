"""
NodeChild 数据模型
表示 GROUP 节点的子节点关系（父节点 → 子节点）
"""
from sqlalchemy import Column, String, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class NodeChild(Base):
    """节点父子关系表"""
    __tablename__ = 'node_children'
    
    # 复合主键
    parent_node_id = Column(
        String(50),
        ForeignKey('requirement_nodes.id', ondelete='CASCADE'),
        nullable=False
    )
    child_node_id = Column(
        String(50),
        ForeignKey('requirement_nodes.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # 显示顺序
    position = Column(Integer, nullable=False)
    
    # 关系
    parent_node = relationship(
        "RequirementNode",
        foreign_keys=[parent_node_id],
        back_populates="children"
    )
    child_node = relationship(
        "RequirementNode",
        foreign_keys=[child_node_id]
    )
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('parent_node_id', 'child_node_id'),
    )
    
    def __repr__(self):
        return f"<NodeChild {self.parent_node_id} → {self.child_node_id} pos={self.position}>"
