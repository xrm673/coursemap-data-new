"""
UserConcentration 数据模型
用户与 concentration 的关联表（多对多）
"""
from sqlalchemy import Column, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from . import Base


class UserConcentration(Base):
    """用户-Concentration 关联表"""
    __tablename__ = 'user_concentration'

    # 复合主键
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    concentration_id = Column(Integer, ForeignKey('program_concentrations.id', ondelete='RESTRICT'), primary_key=True)

    # 关系
    user = relationship("User", back_populates="user_concentrations")
    concentration = relationship("ProgramConcentration", back_populates="user_concentrations")

    # 索引
    __table_args__ = (
        Index('ix_user_concentration_concentration_id', 'concentration_id'),
    )

    def __repr__(self):
        return f"<UserConcentration user_id={self.user_id} concentration_id={self.concentration_id}>"
