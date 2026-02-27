"""
UserProgram 数据模型
用户与专业的关联表（多对多）
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from . import Base


class UserProgram(Base):
    """用户-专业关联表"""
    __tablename__ = 'user_program'

    # 复合主键
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    program_id = Column(String(20), ForeignKey('programs.id', ondelete='RESTRICT'), primary_key=True)

    # 关系
    user = relationship("User", back_populates="user_programs")
    program = relationship("Program", back_populates="user_programs")

    # 索引
    __table_args__ = (
        Index('ix_user_program_program_id', 'program_id'),
    )

    def __repr__(self):
        return f"<UserProgram user_id={self.user_id} program_id={self.program_id}>"
