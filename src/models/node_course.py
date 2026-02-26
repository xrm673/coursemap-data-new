"""
NodeCourse 数据模型
表示 COURSE_SET 节点包含的课程

字段说明：
- topic: 空字符串表示不限 topic，非空表示只有该 topic 的 enroll group 才算
- combined_group_id: 同一 combined group 的课程共享同一个值；NULL 表示不属于任何 combined group
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, PrimaryKeyConstraint
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
    
    # Combined course 分组 ID（不做外键，仅用于前端分组展示）
    # 同一 combined group 的课程共享同一个值；NULL 表示不属于任何 combined group
    combined_group_id = Column(Integer, nullable=True)
    
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
        combined_str = f" cg={self.combined_group_id}" if self.combined_group_id else ""
        return f"<NodeCourse {self.node_id} → {self.course_id}{topic_str}{combined_str}>"
