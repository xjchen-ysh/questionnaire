import datetime
from applications.extensions import db


class UserNotice(db.Model):
    """用户须知内容表"""
    __tablename__ = 'user_notice'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='须知ID')
    title = db.Column(db.String(200), nullable=False, comment='须知标题')
    content = db.Column(db.Text, nullable=False, comment='须知内容')
    notice_type = db.Column(db.String(50), default='general', comment='须知类型(general通用,privacy隐私,terms条款,safety安全)')
    version = db.Column(db.String(20), default='1.0', comment='版本号')
    status = db.Column(db.Integer, default=1, comment='状态(0禁用,1启用,2归档)')
    is_required = db.Column(db.Boolean, default=True, comment='是否必须确认')
    priority = db.Column(db.Integer, default=0, comment='优先级(数字越大优先级越高)')
    effective_date = db.Column(db.DateTime, comment='生效日期')
    expiry_date = db.Column(db.DateTime, comment='失效日期')
    creator_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=False, comment='创建者ID')
    attachment_path = db.Column(db.String(500), comment='附件路径')
    attachment_name = db.Column(db.String(200), comment='附件名称')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    update_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')
    
    # 关联关系
    confirmations = db.relationship('UserNoticeConfirm', backref='notice', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', backref='created_notices', foreign_keys=[creator_id])
    
    def __repr__(self):
        return f'<UserNotice {self.title}>'
    
    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            0: '禁用',
            1: '启用',
            2: '归档'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def type_text(self):
        """类型文本"""
        type_map = {
            'general': '通用须知',
            'privacy': '隐私政策',
            'terms': '服务条款',
            'safety': '安全须知'
        }
        return type_map.get(self.notice_type, '未知类型')
    
    @property
    def confirmation_count(self):
        """确认数量"""
        return self.confirmations.filter_by(status=1).count()
    
    @property
    def is_active(self):
        """是否有效"""
        now = datetime.datetime.now()
        if self.status != 1:
            return False
        if self.effective_date and self.effective_date > now:
            return False
        if self.expiry_date and self.expiry_date < now:
            return False
        return True
    
    def is_confirmed_by_phone(self, phone):
        """检查是否已被指定手机号确认"""
        return UserNoticeConfirm.query.filter_by(
            notice_id=self.id,
            phone=phone,
            status=1
        ).first() is not None
    
    def get_phone_confirmation(self, phone):
        """获取手机号确认记录"""
        return UserNoticeConfirm.query.filter_by(
            notice_id=self.id,
            phone=phone
        ).order_by(UserNoticeConfirm.create_at.desc()).first()
    
    @classmethod
    def get_active_notices(cls, notice_type=None):
        """获取有效的须知列表"""
        query = cls.query.filter_by(status=1)
        if notice_type:
            query = query.filter_by(notice_type=notice_type)
        
        now = datetime.datetime.now()
        query = query.filter(
            db.or_(
                cls.effective_date.is_(None),
                cls.effective_date <= now
            )
        ).filter(
            db.or_(
                cls.expiry_date.is_(None),
                cls.expiry_date > now
            )
        )
        
        return query.order_by(cls.priority.desc(), cls.sort_order.asc()).all()
    
    @classmethod
    def get_required_notices_for_phone(cls, phone):
        """获取手机号需要确认的须知列表"""
        # 获取所有有效且必须确认的须知
        active_notices = cls.get_active_notices()
        required_notices = [notice for notice in active_notices if notice.is_required]
        
        # 过滤出手机号未确认的须知
        unconfirmed_notices = []
        for notice in required_notices:
            if not notice.is_confirmed_by_phone(phone):
                unconfirmed_notices.append(notice)
        
        return unconfirmed_notices


class UserNoticeConfirm(db.Model):
    """用户须知确认记录表"""
    __tablename__ = 'user_notice_confirm'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='确认记录ID')
    notice_id = db.Column(db.Integer, db.ForeignKey('user_notice.id'), nullable=False, comment='须知ID')
    phone = db.Column(db.String(20), comment='手机号码')
    user_ip = db.Column(db.String(45), comment='用户IP地址')
    user_agent = db.Column(db.String(500), comment='用户代理信息')
    confirm_method = db.Column(db.String(20), default='web', comment='确认方式(web网页,mobile手机,api接口)')
    status = db.Column(db.Integer, default=1, comment='状态(0取消确认,1已确认)')
    remark = db.Column(db.String(500), comment='备注')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='确认时间')
    update_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='更新时间')
    
    # 复合索引
    __table_args__ = (
        db.Index('idx_notice_phone', 'notice_id', 'phone'),
        db.Index('idx_phone_confirm_time', 'phone', 'create_at'),
        db.Index('idx_notice_confirm_time', 'notice_id', 'create_at'),
    )
    
    def __repr__(self):
        return f'<UserNoticeConfirm notice_id={self.notice_id} phone={self.phone}>'
    
    @property
    def status_text(self):
        """状态文本"""
        status_map = {
            0: '取消确认',
            1: '已确认'
        }
        return status_map.get(self.status, '未知')
    
    @property
    def method_text(self):
        """确认方式文本"""
        method_map = {
            'web': '网页确认',
            'mobile': '手机确认',
            'api': 'API确认'
        }
        return method_map.get(self.confirm_method, '未知方式')
    
    @classmethod
    def create_confirmation(cls, notice_id, phone, user_ip=None, user_agent=None, confirm_method='web', remark=None):
        """创建确认记录"""
        # 检查是否已存在确认记录
        existing = cls.query.filter_by(
            notice_id=notice_id,
            phone=phone,
            status=1
        ).first()
        
        if existing:
            return existing
        
        # 创建新的确认记录
        confirmation = cls(
            notice_id=notice_id,
            phone=phone,
            user_ip=user_ip,
            user_agent=user_agent,
            confirm_method=confirm_method,
            remark=remark
        )
        
        db.session.add(confirmation)
        return confirmation
    
    @classmethod
    def get_phone_confirmations(cls, phone, notice_type=None):
        """获取手机号的确认记录"""
        query = cls.query.filter_by(phone=phone, status=1)
        
        if notice_type:
            query = query.join(UserNotice).filter(UserNotice.notice_type == notice_type)
        
        return query.order_by(cls.create_at.desc()).all()
    
    def get_notice_confirmations(self, limit=None):
        """获取须知的确认记录"""
        query = UserNoticeConfirm.query.filter_by(notice_id=self.id, status=1)
        query = query.order_by(UserNoticeConfirm.create_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()