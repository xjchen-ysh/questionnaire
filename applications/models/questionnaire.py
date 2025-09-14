import datetime
from applications.extensions import db


class Questionnaire(db.Model):
    __tablename__ = 'questionnaire'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='用户ID')
    title = db.Column(db.String(200), nullable=False, comment='问卷标题')
    description = db.Column(db.Text, comment='问卷描述')
    questionnaire_type = db.Column(db.String(50), default='survey', comment='问卷类型(survey调查,feedback反馈,evaluation评估,registration报名)')
    status = db.Column(db.Integer, default=0, comment='状态(0草稿,1发布,2停止,3归档)')
    is_published = db.Column(db.Boolean, default=False, comment='是否发布')
    creator_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), comment='创建者ID')
    start_time = db.Column(db.DateTime, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    max_responses = db.Column(db.Integer, comment='最大回答数量')
    allow_anonymous = db.Column(db.Boolean, default=True, comment='允许匿名回答')
    require_login = db.Column(db.Boolean, default=False, comment='需要登录')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    update_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')
    
    # 关联关系
    questions = db.relationship('Question', backref='questionnaire', lazy='dynamic', cascade='all, delete-orphan')
    responses = db.relationship('QuestionnaireResponse', backref='questionnaire', lazy='dynamic')
    
    def __repr__(self):
        return f'<Questionnaire {self.title}>'
    
    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            0: '草稿',
            1: '发布',
            2: '停止',
            3: '归档'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def response_count(self):
        """回答数量"""
        return self.responses.filter_by(status=1).count()
    
    @property
    def question_count(self):
        """问题数量"""
        return self.questions.count()
    
    @property
    def type_text(self):
        """问卷类型文本"""
        type_map = {
            'survey': '调查问卷',
            'feedback': '反馈问卷',
            'evaluation': '评估问卷',
            'registration': '报名问卷'
        }
        return type_map.get(self.questionnaire_type, '未知类型')
    
    def can_submit(self):
        """是否可以提交回答"""
        if not self.is_published:  # 未发布状态
            return False
        
        now = datetime.datetime.now()
        
        # 检查时间范围
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        
        # 检查最大回答数量
        if self.max_responses and self.response_count >= self.max_responses:
            return False
        
        return True


class Question(db.Model):
    """问题模型"""
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='问题ID')
    questionnaire_id = db.Column(db.Integer, db.ForeignKey('questionnaire.id'), nullable=False, comment='问卷ID')
    title = db.Column(db.String(500), nullable=False, comment='问题标题')
    description = db.Column(db.Text, comment='问题描述')
    question_type = db.Column(db.String(20), nullable=False, comment='问题类型(single_choice,multiple_choice,text,textarea,rating,date)')
    is_required = db.Column(db.Boolean, default=False, comment='是否必填')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    config = db.Column(db.JSON, comment='问题配置(JSON格式,存储特殊配置)')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    update_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')
    
    # 关联关系
    options = db.relationship('QuestionOption', backref='question', lazy='dynamic', cascade='all, delete-orphan')
    answers = db.relationship('QuestionAnswer', backref='question', lazy='dynamic')
    
    def __repr__(self):
        return f'<Question {self.title}>'
    
    @property
    def type_text(self):
        """问题类型文本"""
        type_map = {
            'single_choice': '单选题',
            'multiple_choice': '多选题',
            'text': '单行文本',
            'textarea': '多行文本',
            'rating': '评分题',
            'date': '日期题'
        }
        return type_map.get(self.question_type, '未知类型')
    
    @property
    def has_options(self):
        """是否有选项"""
        return self.question_type in ['single_choice', 'multiple_choice']
    
    def get_options_list(self):
        """获取选项列表"""
        return self.options.order_by(QuestionOption.sort_order).all()
    
    def validate_answer(self, answer_data):
        """验证答案"""
        if self.is_required and not answer_data:
            return False, '此题为必填项'
        
        if not answer_data:
            return True, ''
        
        # 根据题型验证答案
        if self.question_type == 'single_choice':
            if not isinstance(answer_data, str):
                return False, '单选题答案格式错误'
            # 验证选项是否存在
            option = self.options.filter_by(id=answer_data).first()
            if not option:
                return False, '选择的选项不存在'
        
        elif self.question_type == 'multiple_choice':
            if not isinstance(answer_data, list):
                return False, '多选题答案格式错误'
            # 验证所有选项是否存在
            for option_id in answer_data:
                option = self.options.filter_by(id=option_id).first()
                if not option:
                    return False, f'选项{option_id}不存在'
        
        elif self.question_type in ['text', 'textarea']:
            if not isinstance(answer_data, str):
                return False, '文本答案格式错误'
            # 可以添加长度限制等验证
            config = self.config or {}
            max_length = config.get('max_length')
            if max_length and len(answer_data) > max_length:
                return False, f'文本长度不能超过{max_length}个字符'
        
        elif self.question_type == 'rating':
            try:
                rating = float(answer_data)
                config = self.config or {}
                min_rating = config.get('min_rating', 1)
                max_rating = config.get('max_rating', 5)
                if not (min_rating <= rating <= max_rating):
                    return False, f'评分必须在{min_rating}-{max_rating}之间'
            except (ValueError, TypeError):
                return False, '评分格式错误'
        
        return True, ''


class QuestionOption(db.Model):
    """问题选项模型"""
    __tablename__ = 'question_option'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='选项ID')
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False, comment='问题ID')
    option_text = db.Column(db.String(500), nullable=False, comment='选项文本')
    option_value = db.Column(db.String(100), comment='选项值')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_other = db.Column(db.Boolean, default=False, comment='是否为其他选项')
    is_correct = db.Column(db.Boolean, default=False, comment='是否为正确答案')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    
    def __repr__(self):
        return f'<QuestionOption {self.option_text}>'
    
    @property
    def display_text(self):
        """显示文本"""
        if self.is_other:
            return f'{self.option_text}(其他)'
        return self.option_text