"""
EnrollGroup 匹配逻辑服务
用于判断不同学期的 EnrollGroup 是否相同
"""


class EnrollGroupMatcher:
    """EnrollGroup 匹配器"""
    
    @staticmethod
    def calculate_matching_key(eg_data):
        """
        从 API 数据计算 matching_type 和 matching_key
        
        判断规则（优先级递减）：
        1. 如果任何一个 section 有 topic → 用 topic 匹配
        2. 其他情况 → 用第一个 section 的 section_name 匹配
        
        Args:
            eg_data: 从 Cornell API 获取的 enrollGroup 数据字典
            
        Returns:
            tuple: (matching_type, matching_key)
                - matching_type: "topic", "section_name"
                - matching_key: 具体的匹配值
        """
        class_sections_data = eg_data.get("classSections", [])
        
        if not class_sections_data:
            # 极少见的情况：没有 sections
            return ("section_name", "UNKNOWN")
        
        # 规则 1：检查是否有 topic
        for cs_data in class_sections_data:
            topic = cs_data.get("topicDescription", "").strip()
            if topic:  # topic 不为空
                return ("topic", topic)
        
        # 规则 2：使用第一个 section 的 section_name
        first_section = class_sections_data[0]
        section_type = first_section.get("ssrComponent", "")
        section_number = first_section.get("section", "")
        section_name = section_type + section_number
        
        return ("section_name", section_name)
    
    @staticmethod
    def find_matching_group(session, course_id, matching_type, matching_key):
        """
        在数据库中查找匹配的 EnrollGroup
        
        Args:
            session: SQLAlchemy 数据库会话
            course_id: 课程 ID
            matching_type: 匹配类型
            matching_key: 匹配值
            
        Returns:
            EnrollGroup 对象或 None
        """
        from models import EnrollGroup
        
        return session.query(EnrollGroup).filter(
            EnrollGroup.course_id == course_id,
            EnrollGroup.matching_type == matching_type,
            EnrollGroup.matching_key == matching_key
        ).first()
