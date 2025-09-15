# -*- coding: utf-8 -*-
"""
前端用户API接口模块
包含H5页面路由和用户相关的API接口
"""

import os
import re
import uuid
from datetime import datetime
from flask import Blueprint, request, render_template, jsonify, current_app
from werkzeug.utils import secure_filename
from applications.common.utils.http import table_api, success_api, fail_api
from applications.common.utils.validate import str_escape
from applications.models.user_notice import UserNotice, UserNoticeConfirm
from applications.models import User
from applications.extensions import db
from plugins.realip import get_user_ip

# 创建蓝图
frontend_bp = Blueprint('frontend', __name__, url_prefix='')

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# 最大文件大小 (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_phone(phone):
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

def generate_filename(original_filename):
    """生成安全的文件名"""
    # 获取文件扩展名
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    # 生成唯一文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_str = str(uuid.uuid4())[:8]
    return f"{timestamp}_{random_str}.{ext}"

def get_upload_path():
    """获取上传文件路径"""
    today = datetime.now()
    upload_dir = os.path.join(
        current_app.root_path, 
        'static', 
        'uploads', 
        'notice', 
        today.strftime('%Y'),
        today.strftime('%m'),
        today.strftime('%d')
    )
    # 确保目录存在
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

# ==================== H5页面路由 ====================

@frontend_bp.route('/h5/notice/<int:notice_id>')
def h5_notice_page(notice_id):
    """H5须知页面"""
    try:
        # 查询须知信息
        notice = UserNotice.query.filter_by(id=notice_id, status=1).first()
        if not notice:
            return render_template('errors/404.html'), 404
        
        # 检查须知是否在有效期内
        now = datetime.now()
        if notice.effective_date and now < notice.effective_date:
            return render_template('errors/404.html'), 404
        if notice.expiry_date and now > notice.expiry_date:
            return render_template('errors/404.html'), 404
        
        # 渲染H5页面
        return render_template('frontend/notice.html', notice=notice)
    
    except Exception as e:
        current_app.logger.error(f"H5页面访问错误: {str(e)}")
        return render_template('errors/500.html'), 500

# ==================== API接口 ====================

@frontend_bp.route('/api/notice/<int:notice_id>', methods=['GET'])
def get_notice_api(notice_id):
    """获取须知内容API"""
    try:
        # 查询须知信息
        notice = UserNotice.query.filter_by(id=notice_id, status=1).first()
        if not notice:
            return fail_api(msg="须知不存在或已下线")
        
        # 检查须知是否在有效期内
        now = datetime.now()
        if notice.effective_date and now < notice.effective_date:
            return fail_api(msg="须知尚未生效")
        if notice.expiry_date and now > notice.expiry_date:
            return fail_api(msg="须知已过期")
        
        # 构造返回数据
        data = {
            'id': notice.id,
            'title': notice.title,
            'content': notice.content,
            'notice_type': notice.notice_type,
            'version': notice.version,
            'is_required': notice.is_required,
            'priority': notice.priority,
            'effective_date': notice.effective_date.strftime('%Y-%m-%d %H:%M:%S') if notice.effective_date else None,
            'expiry_date': notice.expiry_date.strftime('%Y-%m-%d %H:%M:%S') if notice.expiry_date else None,
            'attachment_path': notice.attachment_path,
            'attachment_name': notice.attachment_name,
            'create_at': notice.create_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(code=0, msg="成功", data=data)
    
    except Exception as e:
        current_app.logger.error(f"获取须知API错误: {str(e)}")
        return fail_api(msg="服务器内部错误")

@frontend_bp.route('/api/notice/confirm', methods=['POST'])
def confirm_notice_api():
    """用户确认须知API"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return fail_api(msg="请求数据格式错误")
        
        # 验证必填字段
        notice_id = data.get('notice_id')
        phone = str_escape(data.get('phone', '').strip())
        remark = str_escape(data.get('remark', '').strip())
        
        if not notice_id:
            return fail_api(msg="须知ID不能为空")
        if not phone:
            return fail_api(msg="手机号不能为空")
        if not validate_phone(phone):
            return fail_api(msg="手机号格式不正确")
        
        # 验证须知是否存在且有效
        notice = UserNotice.query.filter_by(id=notice_id, status=1).first()
        if not notice:
            return fail_api(msg="须知不存在或已下线")
        
        # 检查须知是否在有效期内
        now = datetime.now()
        if notice.effective_date and now < notice.effective_date:
            return fail_api(msg="须知尚未生效")
        if notice.expiry_date and now > notice.expiry_date:
            return fail_api(msg="须知已过期")
        
        # 检查是否已经确认过
        existing_confirm = UserNoticeConfirm.query.filter_by(
            notice_id=notice_id,
            phone=phone,
            status=1
        ).first()
        
        if existing_confirm:
            return fail_api(msg="您已经确认过此须知")
        
        # 获取用户IP和User-Agent
        user_ip = get_user_ip(request)
        user_agent = request.headers.get('User-Agent', '')[:500]  # 限制长度
        
        # 创建确认记录
        confirm_record = UserNoticeConfirm(
            notice_id=notice_id,
            phone=phone,
            user_ip=user_ip,
            user_agent=user_agent,
            confirm_method='web',
            status=1,
            remark=remark
        )
        

        
        db.session.add(confirm_record)
        db.session.commit()
        
        return success_api(msg="确认成功", data={'confirm_id': confirm_record.id})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"确认须知API错误: {str(e)}")
        return fail_api(msg="服务器内部错误")

@frontend_bp.route('/api/upload/photo', methods=['POST'])
def upload_photo_api():
    """照片上传API"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return fail_api(msg="没有选择文件")
        
        file = request.files['file']
        if file.filename == '':
            return fail_api(msg="没有选择文件")
        
        # 验证文件类型
        if not allowed_file(file.filename):
            return fail_api(msg="不支持的文件类型，请上传PNG、JPG、JPEG或GIF格式的图片")
        
        # 验证文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        if file_size > MAX_FILE_SIZE:
            return fail_api(msg="文件大小不能超过5MB")
        
        # 生成安全的文件名
        filename = generate_filename(file.filename)
        
        # 获取上传路径
        upload_dir = get_upload_path()
        file_path = os.path.join(upload_dir, filename)
        
        # 保存文件
        file.save(file_path)
        
        # 生成相对路径用于数据库存储和前端访问
        today = datetime.now()
        relative_path = f"/static/uploads/notice/{today.strftime('%Y')}/{today.strftime('%m')}/{today.strftime('%d')}/{filename}"
        
        return success_api(
            msg="上传成功",
            data={
                'filename': filename,
                'path': relative_path,
                'size': file_size
            }
        )
    
    except Exception as e:
        current_app.logger.error(f"照片上传API错误: {str(e)}")
        return fail_api(msg="上传失败，请重试")

# ==================== 辅助API ====================

@frontend_bp.route('/api/notice/check_confirm', methods=['POST'])
def check_confirm_api():
    """检查用户是否已确认须知"""
    try:
        data = request.get_json()
        if not data:
            return fail_api(msg="请求数据格式错误")
        
        notice_id = data.get('notice_id')
        phone = str_escape(data.get('phone', '').strip())
        
        if not notice_id or not phone:
            return fail_api(msg="参数不完整")
        
        if not validate_phone(phone):
            return fail_api(msg="手机号格式不正确")
        
        # 查询确认记录
        confirm_record = UserNoticeConfirm.query.filter_by(
            notice_id=notice_id,
            phone=phone,
            status=1
        ).first()
        
        if confirm_record:
            return success_api(
                data={
                    'confirmed': True,
                    'confirm_time': confirm_record.create_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            )
        else:
            return success_api(data={'confirmed': False})
    
    except Exception as e:
        current_app.logger.error(f"检查确认状态API错误: {str(e)}")
        return fail_api(msg="服务器内部错误")

@frontend_bp.route('/api/notice/list', methods=['GET'])
def get_notice_list_api():
    """获取有效须知列表API"""
    try:
        # 获取查询参数
        notice_type = request.args.get('type')
        
        # 构建查询条件
        query = UserNotice.query.filter_by(status=1)
        
        if notice_type:
            query = query.filter_by(notice_type=notice_type)
        
        # 检查有效期
        now = datetime.now()
        query = query.filter(
            db.or_(
                UserNotice.effective_date.is_(None),
                UserNotice.effective_date <= now
            )
        ).filter(
            db.or_(
                UserNotice.expiry_date.is_(None),
                UserNotice.expiry_date >= now
            )
        )
        
        # 按优先级和排序字段排序
        notices = query.order_by(
            UserNotice.priority.desc(),
            UserNotice.sort_order.asc(),
            UserNotice.create_at.desc()
        ).all()
        
        # 构造返回数据
        data = []
        for notice in notices:
            data.append({
                'id': notice.id,
                'title': notice.title,
                'notice_type': notice.notice_type,
                'version': notice.version,
                'is_required': notice.is_required,
                'priority': notice.priority,
                'effective_date': notice.effective_date.strftime('%Y-%m-%d %H:%M:%S') if notice.effective_date else None,
                'expiry_date': notice.expiry_date.strftime('%Y-%m-%d %H:%M:%S') if notice.expiry_date else None,
                'create_at': notice.create_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify(success=True, msg="成功", data=data)
    
    except Exception as e:
        current_app.logger.error(f"获取须知列表API错误: {str(e)}")
        return fail_api(msg="服务器内部错误")