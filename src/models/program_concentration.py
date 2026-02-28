"""
ProgramConcentration 数据模型
表示专业下的 concentration 选项
"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from . import Base


class ProgramConcentration(Base):
    """专业 Concentration 表"""
    __tablename__ = 'program_concentrations'

    # 主键：自增整数（方便被 users 等表 FK 引用）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键：所属专业
    program_id = Column(
        String(20),
        ForeignKey('programs.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Concentration 名称
    concentration_name = Column(String(255), nullable=False)

    # 关系
    program = relationship("Program", back_populates="program_concentrations")
    user_concentrations = relationship(
        "UserConcentration",
        back_populates="concentration"
    )
    requirements = relationship(
        "Requirement",
        back_populates="concentration"
    )

    # 唯一约束：同一专业下 concentration 名称不重复
    __table_args__ = (
        UniqueConstraint('program_id', 'concentration_name', name='uq_program_concentration'),
    )

    def __repr__(self):
        return f"<ProgramConcentration {self.id}: {self.program_id} - {self.concentration_name}>"

    def __str__(self):
        return f"{self.program_id} / {self.concentration_name}"
