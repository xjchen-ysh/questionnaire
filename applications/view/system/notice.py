from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename

from applications.common import curd
from applications.common.utils import validate
from applications.common.utils.http import success_api, fail_api, table_api
from applications.common.utils.rights import authorize
from applications.common.utils.validate import str_escape
from applications.extensions import db
from applications.models.user_notice import UserNotice, UserNoticeConfirm

bp = Blueprint("notice", __name__, url_prefix="/notice")


@bp.get("/")
@authorize("system:notice:main", log=True)
def main():
    """须知管理主页面"""
    return render_template("system/notice/main.html")


@bp.get("/data")
@authorize("system:notice:main", log=True)
def data():
    """须知列表查询接口"""
    # 获取查询参数
    title = str_escape(request.args.get("title", type=str))
    notice_type = str_escape(request.args.get("notice_type", type=str))
    status = request.args.get("status", type=int)
    
    # 构建查询条件
    filters = []
    if title:
        filters.append(UserNotice.title.contains(title))
    if notice_type:
        filters.append(UserNotice.notice_type == notice_type)
    if status is not None:
        filters.append(UserNotice.status == status)
    
    # 执行查询
    query = (
        UserNotice.query.filter(*filters)
        .order_by(UserNotice.priority.desc(), UserNotice.sort_order.asc())
        .layui_paginate()
    )
    
    return table_api(
        data=[
            {
                "id": notice.id,
                "title": notice.title,
                "notice_type": notice.notice_type,
                "type_text": notice.type_text,
                "version": notice.version,
                "status": notice.status,
                "status_text": notice.status_text,
                "is_required": notice.is_required,
                "priority": notice.priority,
                "effective_date": (
                    notice.effective_date.strftime("%Y-%m-%d %H:%M:%S")
                    if notice.effective_date
                    else None
                ),
                "expiry_date": (
                    notice.expiry_date.strftime("%Y-%m-%d %H:%M:%S")
                    if notice.expiry_date
                    else None
                ),
                "confirmation_count": notice.confirmation_count,
                "is_active": notice.is_active,
                "sort_order": notice.sort_order,
                "create_at": notice.create_at.strftime("%Y-%m-%d %H:%M:%S"),
                "update_at": notice.update_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for notice in query.items
        ],
        count=query.total,
    )


@bp.post("/save")
@authorize("system:notice:add", log=True)
def save():
    """须知新增接口"""
    req_json = request.get_json(force=True)
    
    # 验证必填字段
    title = str_escape(req_json.get("title"))
    content = str_escape(req_json.get("content"))
    if not title or not content:
        return fail_api(msg="标题和内容不能为空")
    
    # 处理时间字段
    effective_date = req_json.get("effective_date")
    expiry_date = req_json.get("expiry_date")
    
    effective_date_obj = None
    expiry_date_obj = None
    
    if effective_date:
        try:
            effective_date_obj = datetime.strptime(effective_date, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="生效日期格式错误")
    
    if expiry_date:
        try:
            expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="失效日期格式错误")
    
    # 验证日期逻辑
    if effective_date_obj and expiry_date_obj and expiry_date_obj <= effective_date_obj:
        return fail_api(msg="失效日期必须晚于生效日期")
    
    # 获取创建者ID（从当前登录用户获取）
    from flask_login import current_user
    creator_id = current_user.id if current_user.is_authenticated else 1
    
    # 创建须知记录
    notice = UserNotice(
        title=title,
        content=content,
        notice_type=str_escape(req_json.get("notice_type", "general")),
        version=str_escape(req_json.get("version", "1.0")),
        status=req_json.get("status", 1),
        is_required=bool(req_json.get("is_required", True)),
        priority=req_json.get("priority", 0),
        effective_date=effective_date_obj,
        expiry_date=expiry_date_obj,
        creator_id=creator_id,
        attachment_path=str_escape(req_json.get("attachment_path")),
        attachment_name=str_escape(req_json.get("attachment_name")),
        sort_order=req_json.get("sort_order", 0),
    )
    
    db.session.add(notice)
    db.session.commit()
    
    return success_api(msg="须知创建成功")


@bp.post("/update")
@authorize("system:notice:edit", log=True)
def update():
    """须知编辑接口"""
    req_json = request.get_json(force=True)
    
    # 获取须知ID
    notice_id = req_json.get("id")
    if not notice_id:
        return fail_api(msg="须知ID不能为空")
    
    # 查询须知记录
    notice = UserNotice.query.get(notice_id)
    if not notice:
        return fail_api(msg="须知不存在")
    
    # 验证必填字段
    title = str_escape(req_json.get("title"))
    content = str_escape(req_json.get("content"))
    if not title or not content:
        return fail_api(msg="标题和内容不能为空")
    
    # 处理时间字段
    effective_date = req_json.get("effective_date")
    expiry_date = req_json.get("expiry_date")
    
    effective_date_obj = None
    expiry_date_obj = None
    
    if effective_date:
        try:
            effective_date_obj = datetime.strptime(effective_date, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="生效日期格式错误")
    
    if expiry_date:
        try:
            expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="失效日期格式错误")
    
    # 验证日期逻辑
    if effective_date_obj and expiry_date_obj and expiry_date_obj <= effective_date_obj:
        return fail_api(msg="失效日期必须晚于生效日期")
    
    # 更新须知记录
    notice.title = title
    notice.content = content
    notice.notice_type = str_escape(req_json.get("notice_type", notice.notice_type))
    notice.version = str_escape(req_json.get("version", notice.version))
    notice.status = req_json.get("status", notice.status)
    notice.is_required = bool(req_json.get("is_required", notice.is_required))
    notice.priority = req_json.get("priority", notice.priority)
    notice.effective_date = effective_date_obj
    notice.expiry_date = expiry_date_obj
    notice.attachment_path = str_escape(req_json.get("attachment_path", notice.attachment_path))
    notice.attachment_name = str_escape(req_json.get("attachment_name", notice.attachment_name))
    notice.sort_order = req_json.get("sort_order", notice.sort_order)
    
    db.session.commit()
    
    return success_api(msg="须知更新成功")


@bp.post("/remove")
@authorize("system:notice:remove", log=True)
def remove():
    """须知删除接口"""
    req_json = request.get_json(force=True)
    
    # 获取须知ID
    notice_id = req_json.get("id")
    if not notice_id:
        return fail_api(msg="须知ID不能为空")
    
    # 查询须知记录
    notice = UserNotice.query.get(notice_id)
    if not notice:
        return fail_api(msg="须知不存在")
    
    # 检查是否有确认记录
    confirmation_count = notice.confirmations.count()
    if confirmation_count > 0:
        return fail_api(msg=f"该须知已有{confirmation_count}条确认记录，不能删除")
    
    # 删除须知记录
    db.session.delete(notice)
    db.session.commit()
    
    return success_api(msg="须知删除成功")


@bp.get("/confirm/data")
@authorize("system:notice:confirm:main", log=True)
def confirm_data():
    """确认记录查询接口"""
    # 获取查询参数
    notice_id = request.args.get("notice_id", type=int)
    phone = str_escape(request.args.get("phone", type=str))
    confirm_method = str_escape(request.args.get("confirm_method", type=str))
    status = request.args.get("status", type=int)
    
    # 构建查询条件
    filters = []
    if notice_id:
        filters.append(UserNoticeConfirm.notice_id == notice_id)
    if phone:
        filters.append(UserNoticeConfirm.phone.contains(phone))
    if confirm_method:
        filters.append(UserNoticeConfirm.confirm_method == confirm_method)
    if status is not None:
        filters.append(UserNoticeConfirm.status == status)
    
    # 执行查询
    query = (
        UserNoticeConfirm.query.filter(*filters)
        .join(UserNotice)
        .order_by(UserNoticeConfirm.create_at.desc())
        .layui_paginate()
    )
    
    return table_api(
        data=[
            {
                "id": confirm.id,
                "notice_id": confirm.notice_id,
                "notice_title": confirm.notice.title,
                "notice_type": confirm.notice.notice_type,
                "notice_type_text": confirm.notice.type_text,
                "phone": confirm.phone,
                "user_ip": confirm.user_ip,
                "user_agent": confirm.user_agent,
                "confirm_method": confirm.confirm_method,
                "method_text": confirm.method_text,
                "status": confirm.status,
                "status_text": confirm.status_text,
                "remark": confirm.remark,
                "create_at": confirm.create_at.strftime("%Y-%m-%d %H:%M:%S"),
                "update_at": confirm.update_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for confirm in query.items
        ],
        count=query.total,
    )


@bp.get("/confirm/export")
@authorize("system:notice:confirm:export", log=True)
def confirm_export():
    """确认记录导出接口"""
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    
    # 获取查询参数
    notice_id = request.args.get("notice_id", type=int)
    phone = str_escape(request.args.get("phone", type=str))
    confirm_method = str_escape(request.args.get("confirm_method", type=str))
    status = request.args.get("status", type=int)
    
    # 构建查询条件
    filters = []
    if notice_id:
        filters.append(UserNoticeConfirm.notice_id == notice_id)
    if phone:
        filters.append(UserNoticeConfirm.phone.contains(phone))
    if confirm_method:
        filters.append(UserNoticeConfirm.confirm_method == confirm_method)
    if status is not None:
        filters.append(UserNoticeConfirm.status == status)
    
    # 执行查询
    confirmations = (
        UserNoticeConfirm.query.filter(*filters)
        .join(UserNotice)
        .order_by(UserNoticeConfirm.create_at.desc())
        .all()
    )
    
    # 准备导出数据
    export_data = []
    for confirm in confirmations:
        export_data.append({
            "确认记录ID": confirm.id,
            "须知ID": confirm.notice_id,
            "须知标题": confirm.notice.title,
            "须知类型": confirm.notice.type_text,
            "手机号码": confirm.phone,
            "用户IP": confirm.user_ip,
            "确认方式": confirm.method_text,
            "状态": confirm.status_text,
            "备注": confirm.remark or "",
            "确认时间": confirm.create_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    # 创建Excel文件
    df = pd.DataFrame(export_data)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='确认记录', index=False)
    
    output.seek(0)
    
    # 生成文件名
    filename = f"须知确认记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.get("/add")
@authorize("system:notice:add", log=True)
def add():
    """须知新增页面"""
    return render_template("system/notice/add.html")


@bp.get("/edit/<int:notice_id>")
@authorize("system:notice:edit", log=True)
def edit(notice_id):
    """须知编辑页面"""
    notice = curd.get_one_by_id(UserNotice, notice_id)
    if not notice:
        return render_template("system/error/404.html")
    return render_template("system/notice/edit.html", notice=notice)


@bp.get("/detail/<int:notice_id>")
@authorize("system:notice:main", log=True)
def detail(notice_id):
    """须知详情页面"""
    notice = curd.get_one_by_id(UserNotice, notice_id)
    if not notice:
        return render_template("system/error/404.html")
    return render_template("system/notice/detail.html", notice=notice)


@bp.get("/confirm/main")
@authorize("system:notice:confirm:main", log=True)
def confirm_main():
    """确认记录管理页面"""
    return render_template("system/notice/confirm_main.html")