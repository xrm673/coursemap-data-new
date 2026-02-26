"""
NodeCourse 数据模型
表示 COURSE_SET 节点包含的课程
topic 字段：空字符串表示不限 topic，非空表示只有该 topic 的 enroll group 才算
"""
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, PrimaryKeyConstraint
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
    # topic 限定：""表示不限，非空表示只有该 topic 的 enroll group 才满足
    topic = Column(String(255), nullable=False, default="")
    
    # 备注
    comment = Column(Text, nullable=True)
    
    # 是否为系推荐课程
    recommended = Column(Boolean, nullable=False, default=False)
    
    # 关系
    node = relationship("RequirementNode", back_populates="courses")
    course = relationship("Course")
    
    # 表级约束
    __table_args__ = (
        PrimaryKeyConstraint('node_id', 'course_id', 'topic'),
    )
    
    def __repr__(self):
        topic_str = f" topic='{self.topic}'" if self.topic else ""
        return f"<NodeCourse {self.node_id} → {self.course_id}{topic_str}>"
