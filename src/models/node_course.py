"""
NodeCourse 数据模型
表示 COURSE_SET 节点包含的课程
"""
from sqlalchemy import Column, String, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from . import Base


class NodeCourse(Base):
    """节点-课程关联表"""
    __tablename__ = 'node_courses'
    
    # 复合主键
    node_id = Column(
        String(50),
        ForeignKey('requirement_nodes.id', ondelete='CASCADE'),
        nullable=False
    )
    course_id = Column(
        String(20),
        ForeignKey('courses.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # 关系
    node = relationship("RequirementNode", back_populates="courses")
    course = relationship("Course")
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('node_id', 'course_id'),
    )
    
    def __repr__(self):
        return f"<NodeCourse {self.node_id} → {self.course_id}>"
