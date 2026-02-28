"""
数据模型包
"""
from sqlalchemy.orm import declarative_base

# 创建 ORM 基类
Base = declarative_base()

# 导出所有模型 — 课程相关
from .subject import Subject
from .course import Course
from .course_attribute import CourseAttribute
from .enroll_group import EnrollGroup
from .class_section import ClassSection
from .meeting import Meeting
from .instructor import Instructor
from .meeting_instructor import MeetingInstructor
from .combined_group import CombinedGroup

# 导出所有模型 — 用户相关
from .user import User
from .user_program import UserProgram
from .user_course import UserCourse
from .user_course_section import UserCourseSection
from .user_concentration import UserConcentration

# 导出所有模型 — 学院相关
from .college import College
from .college_program import CollegeProgram
from .college_subject import CollegeSubject

# 导出所有模型 — 专业要求相关
from .program import Program
from .program_subject import ProgramSubject
from .program_concentration import ProgramConcentration
from .requirement import Requirement
from .requirement_set import RequirementSet
from .requirement_set_requirement import RequirementSetRequirement
from .requirement_domain import RequirementDomain
from .requirement_domain_membership import RequirementDomainMembership
from .requirement_node import RequirementNode
from .node_child import NodeChild
from .node_course import NodeCourse

__all__ = [
    'Base',
    # 课程相关
    'Subject',
    'Course', 
    'CourseAttribute', 
    'EnrollGroup', 
    'ClassSection',
    'Meeting',
    'Instructor',
    'MeetingInstructor',
    'CombinedGroup',
    # 用户相关
    'User',
    'UserProgram',
    'UserCourse',
    'UserCourseSection',
    'UserConcentration',
    # 学院相关
    'College',
    'CollegeProgram',
    'CollegeSubject',
    # 专业要求相关
    'Program',
    'ProgramSubject',
    'ProgramConcentration',
    'Requirement',
    'RequirementSet',
    'RequirementSetRequirement',
    'RequirementDomain',
    'RequirementDomainMembership',
    'RequirementNode',
    'NodeChild',
    'NodeCourse',
]
