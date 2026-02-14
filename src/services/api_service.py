"""
Cornell API 调用服务
"""
import requests


class APIService:
    """Cornell 课程 API 调用类"""
    
    BASE_URL = "https://classes.cornell.edu/api/2.0/search/classes.json"
    
    def __init__(self):
        self.session = requests.Session()
    
    def fetch_courses(self, roster, subject):
        """
        从 Cornell API 获取课程数据
        
        Args:
            roster: 学期代码，如 "SP26"
            subject: 学科代码，如 "MATH"
        
        Returns:
            list: 课程数据列表，如果失败返回空列表
        """
        params = {
            'roster': roster,
            'subject': subject
        }
        
        try:
            print(f"正在获取 {roster} {subject} 的课程数据...")
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                classes = data.get('data', {}).get('classes', [])
                print(f"✓ 成功获取 {len(classes)} 门课程")
                return classes
            else:
                print(f"✗ API 返回错误: {data.get('message', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"✗ 网络请求失败: {e}")
            return []
        except ValueError as e:
            print(f"✗ JSON 解析失败: {e}")
            return []
