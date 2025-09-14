import datetime
from applications.extensions import db


class Questionnaire(db.Model):
    __tablename__ = 'admin_questionnaire'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='用户ID')
    name = db.Column(db.String(50), comment='问卷名称')
    remark = db.Column(db.String(255), comment='备注')
    enable = db.Column(db.Integer, default=0, comment='启用')
    create_at = db.Column(db.DateTime, default=datetime.datetime.now, comment='创建时间')
    update_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment='创建时间')
