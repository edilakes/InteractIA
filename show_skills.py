from knowledge_base import KnowledgeBase
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

kb = KnowledgeBase()
skills = kb.get_all_skills()

print(json.dumps(skills, indent=4, cls=DateTimeEncoder))