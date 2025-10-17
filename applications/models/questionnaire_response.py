import datetime
import json
from applications.extensions import db


class QuestionnaireResponse(db.Model):
    """问卷回答模型"""
    __tablename__ = 'questionnaire_response'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='回答ID')
    questionnaire_id = db.Column(db.Integer, db.ForeignKey('questionnaire.id'), nullable=False, comment='问卷ID')
    user_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), comment='用户ID(匿名时为空)')
    phone = db.Column(db.String(20), comment='手机号')
    name = db.Column(db.String(50), comment='用户姓名')
    ip_address = db.Column(db.String(45), comment='IP地址')
    user_agent = db.Column(db.Text, comment='用户代理')
    status = db.Column(db.Integer, default=0, comment='状态(0进行中,1已完成)')
    start_time = db.Column(db.DateTime, default=datetime.datetime.now, comment='开始时间')
    submit_time = db.Column(db.DateTime, comment='提交时间')
    
    # 关联关系
    answers = db.relationship('QuestionAnswer', backref='response', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<QuestionnaireResponse {self.id}>'
    
    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            0: '进行中',
            1: '已完成'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def duration(self):
        """答题时长(秒)"""
        if not self.submit_time:
            return None
        return int((self.submit_time - self.start_time).total_seconds())
    
    @property
    def duration_text(self):
        """答题时长文本"""
        duration = self.duration
        if duration is None:
            return '未完成'
        
        minutes = duration // 60
        seconds = duration % 60
        
        if minutes > 0:
            return f'{minutes}分{seconds}秒'
        else:
            return f'{seconds}秒'
    
    def get_answer(self, question_id):
        """获取指定问题的答案"""
        return self.answers.filter_by(question_id=question_id).first()
    
    def get_answers_dict(self):
        """获取所有答案的字典格式"""
        answers_dict = {}
        for answer in self.answers:
            answers_dict[answer.question_id] = {
                'text': answer.answer_text,
                'options': answer.get_option_ids(),
                'value': answer.answer_value
            }
        return answers_dict
    
    def submit(self):
        """提交问卷"""
        self.status = 1
        self.submit_time = datetime.datetime.now()
        db.session.commit()
    
    def validate_completion(self):
        """验证问卷是否完整填写"""
        from .question import Question
        
        # 获取所有必填问题
        required_questions = Question.query.filter_by(
            questionnaire_id=self.questionnaire_id,
            is_required=True
        ).all()
        
        # 检查是否都有答案
        for question in required_questions:
            answer = self.get_answer(question.id)
            if not answer or not answer.has_content():
                return False, f'问题「{question.title}」为必填项'
        
        return True, ''


class QuestionAnswer(db.Model):
    """问题回答模型"""
    __tablename__ = 'question_answer'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='答案ID')
    response_id = db.Column(db.Integer, db.ForeignKey('questionnaire_response.id'), nullable=False, comment='回答ID')
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False, comment='问题ID')
    photo_paths = db.Column(db.Text, comment='照片路径列表(JSON格式存储多张图片路径)')
    answer_text = db.Column(db.Text, comment='文本答案')
    answer_option_ids = db.Column(db.String(500), comment='选项ID列表(逗号分隔)')
    answer_value = db.Column(db.String(100), comment='答案值(评分等)')
    option_custom_inputs = db.Column(db.JSON, comment='选项自定义输入内容(JSON格式,键为选项ID,值为输入内容)')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    
    def __repr__(self):
        return f'<QuestionAnswer {self.id}>'

    @property
    def photo_paths_list(self):
        """获取照片路径列表"""
        if not self.photo_paths:
            return []
        try:
            return json.loads(self.photo_paths)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_photo_paths(self, paths_list):
        """设置照片路径列表"""
        if not paths_list:
            self.photo_paths = None
        else:
            self.photo_paths = json.dumps(paths_list)
    
    def get_option_ids(self):
        """获取选项ID列表"""
        if not self.answer_option_ids:
            return []
        return [int(x.strip()) for x in self.answer_option_ids.split(',') if x.strip()]
    
    def set_option_ids(self, option_ids):
        """设置选项ID列表"""
        if isinstance(option_ids, list):
            self.answer_option_ids = ','.join(map(str, option_ids))
        else:
            self.answer_option_ids = str(option_ids)
    
    def get_option_texts(self):
        """获取选项文本列表"""
        from .question import QuestionOption
        
        option_ids = self.get_option_ids()
        if not option_ids:
            return []
        
        options = QuestionOption.query.filter(QuestionOption.id.in_(option_ids)).all()
        return [option.option_text for option in options]
    
    def get_custom_input(self, option_id):
        """获取指定选项的自定义输入内容"""
        if not self.option_custom_inputs:
            return ''
        return self.option_custom_inputs.get(str(option_id), '')
    
    def set_custom_input(self, option_id, input_text):
        """设置指定选项的自定义输入内容"""
        if not self.option_custom_inputs:
            self.option_custom_inputs = {}
        self.option_custom_inputs[str(option_id)] = input_text
    
    def has_content(self):
        """是否有内容"""
        return bool(self.answer_text or self.answer_option_ids or self.answer_value or self.option_custom_inputs)
    
    def get_display_value(self):
        """获取显示值"""
        if self.answer_text:
            return self.answer_text
        elif self.answer_option_ids:
            option_texts = self.get_option_texts()
            display_parts = []
            
            # 获取选项信息以检查是否允许输入
            from .questionnaire import QuestionOption
            option_ids = self.get_option_ids()
            options = QuestionOption.query.filter(QuestionOption.id.in_(option_ids)).all()
            
            for option in options:
                text = option.option_text
                # 如果选项允许输入且有自定义内容，则添加自定义内容
                if option.allow_input:
                    custom_input = self.get_custom_input(option.id)
                    if custom_input:
                        text += f'({custom_input})'
                display_parts.append(text)
            
            return ', '.join(display_parts)
        elif self.answer_value:
            return self.answer_value
        else:
            return ''
    
    @staticmethod
    def create_or_update(response_id, question_id, answer_data, custom_inputs=None):
        """创建或更新答案"""
        answer = QuestionAnswer.query.filter_by(
            response_id=response_id,
            question_id=question_id
        ).first()
        
        if not answer:
            answer = QuestionAnswer(
                response_id=response_id,
                question_id=question_id
            )
            db.session.add(answer)
        
        # 根据数据类型设置答案
        if isinstance(answer_data, str):
            answer.answer_text = answer_data
        elif isinstance(answer_data, list):
            answer.set_option_ids(answer_data)
        elif isinstance(answer_data, (int, float)):
            answer.answer_value = str(answer_data)
        
        # 设置自定义输入内容
        if custom_inputs:
            answer.option_custom_inputs = custom_inputs
        
        return answer