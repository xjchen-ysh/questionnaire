from flask import Blueprint, render_template, request, jsonify
from datetime import datetime

from applications.common import curd
from applications.common.utils import validate
from applications.common.utils.http import success_api, fail_api, table_api
from applications.common.utils.rights import authorize
from applications.common.utils.validate import str_escape
from applications.extensions import db
from applications.models import Questionnaire, QuestionnaireResponse
from applications.models.questionnaire import Question, QuestionOption
from applications.schemas import QuestionnaireOutSchema, QuestionOutSchema, QuestionOptionOutSchema

bp = Blueprint("questionnaire", __name__, url_prefix="/questionnaire")


@bp.get("/")
@authorize("system:questionnaire:main", log=True)
def main():
    return render_template("system/questionnaire/main.html")


@bp.get("/data")
@authorize("system:questionnaire:data", log=True)
def data():
    questionnaire_name = str_escape(request.args.get('questionnaire_name', type=str))
    
    filters = []
    if questionnaire_name:
        filters.append(Questionnaire.title.contains(questionnaire_name))
    query = Questionnaire.query.filter(*filters).order_by(Questionnaire.sort_order).layui_paginate()

    return table_api(
        data=[{
            'id': questionnaire.id,#
            'title': questionnaire.title,
            'description': questionnaire.description,
            'questionnaire_type': questionnaire.questionnaire_type,
            'type_text': questionnaire.type_text,
            'status': questionnaire.status,
            'status_text': questionnaire.status_text,
            'start_time': questionnaire.start_time.strftime('%Y-%m-%d %H:%M:%S') if questionnaire.start_time else None,
            'end_time': questionnaire.end_time.strftime('%Y-%m-%d %H:%M:%S') if questionnaire.end_time else None,
            'max_responses': questionnaire.max_responses,
            'allow_anonymous': questionnaire.allow_anonymous,
            'require_login': questionnaire.require_login,
            'sort_order': questionnaire.sort_order,
            'response_count': questionnaire.response_count,
            'question_count': questionnaire.question_count,
            'create_at': questionnaire.create_at,
            'update_at': questionnaire.update_at,
        } for questionnaire in query.items],
        count=query.total)


@bp.get("/add")
@authorize("system:questionnaire:add", log=True)
def add():
    return render_template("system/questionnaire/add.html")


@bp.get("/tree")
@authorize("system:questionnaire:main", log=True)
def tree():
    questionnaire = Questionnaire.query.order_by(Questionnaire.sort_order).all()
    power_data = curd.model_to_dicts(schema=QuestionnaireOutSchema, data=questionnaire)
    res = {"status": {"code": 200, "message": "默认"}, "data": power_data}
    return jsonify(res)


@bp.post("/save")
@authorize("system:questionnaire:add", log=True)
def save():
    req_json = request.get_json(force=True)
    
    # 处理时间字段
    start_time = req_json.get('start_time')
    end_time = req_json.get('end_time')
    
    start_time_obj = None
    end_time_obj = None
    
    if start_time:
        try:
            start_time_obj = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return fail_api(msg="开始时间格式错误")
    
    if end_time:
        try:
            end_time_obj = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return fail_api(msg="结束时间格式错误")
    
    questionnaire = Questionnaire(
        title=str_escape(req_json.get("title")),
        description=str_escape(req_json.get("description")),
        questionnaire_type=str_escape(req_json.get("questionnaire_type")),
        status=req_json.get("status"),
        start_time=start_time_obj,
        end_time=end_time_obj,
        max_responses=req_json.get("max_responses"),
        allow_anonymous=bool(req_json.get("allow_anonymous")),
        require_login=bool(req_json.get("require_login")),
        sort_order=req_json.get("sort_order", 0),
    )
    db.session.add(questionnaire)
    db.session.commit()
    return success_api(msg="成功")


@bp.get("/edit/<int:id>")
@authorize("system:questionnaire:edit", log=True)
def edit(id):
    questionnaire = curd.get_one_by_id(Questionnaire, id)
    return render_template("system/questionnaire/edit.html", questionnaire=questionnaire)


@bp.get("/design/<int:id>")
@authorize("system:questionnaire:edit", log=True)
def design(id):
    questionnaire = curd.get_one_by_id(Questionnaire, id)
    return render_template("system/questionnaire/design.html", questionnaire=questionnaire)


# 启用
@bp.put("/enable")
@authorize("system:questionnaire:edit", log=True)
def enable():
    id = request.get_json(force=True).get("id")
    if id:
        enable = 1
        d = Questionnaire.query.filter_by(id=id).update({"status": enable})
        if d:
            db.session.commit()
            return success_api(msg="启用成功")
        return fail_api(msg="出错啦")
    return fail_api(msg="数据错误")


# 禁用
@bp.put("/disable")
@authorize("system:questionnaire:edit", log=True)
def dis_enable():
    id = request.get_json(force=True).get("id")
    if id:
        enable = 2
        d = Questionnaire.query.filter_by(id=id).update({"status": enable})
        if d:
            db.session.commit()
            return success_api(msg="禁用成功")
        return fail_api(msg="出错啦")
    return fail_api(msg="数据错误")


@bp.put("/update")
@authorize("system:questionnaire:edit", log=True)
def update():
    req_json = request.get_json(force=True)
    id = str_escape(req_json.get("id"))
    title = str_escape(req_json.get('title'))
    description = str_escape(req_json.get('description'))
    questionnaire_type = str_escape(req_json.get('questionnaire_type'))
    status = req_json.get('status')
    start_time = req_json.get('start_time')
    end_time = req_json.get('end_time')
    max_responses = req_json.get('max_responses')
    allow_anonymous = req_json.get('allow_anonymous')
    require_login = req_json.get('require_login')
    sort_order = req_json.get('sort_order')
    
    # 构建更新数据字典
    update_data = {}
    if title is not None:
        update_data['title'] = title
    if description is not None:
        update_data['description'] = description
    if questionnaire_type is not None:
        update_data['questionnaire_type'] = questionnaire_type
    if status is not None:
        update_data['status'] = status
    if start_time is not None:
        try:
            # 将字符串时间转换为datetime对象
            update_data['start_time'] = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return fail_api(msg="开始时间格式错误")
    if end_time is not None:
        try:
            # 将字符串时间转换为datetime对象
            update_data['end_time'] = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return fail_api(msg="结束时间格式错误")
    if max_responses is not None:
        update_data['max_responses'] = max_responses
    if allow_anonymous is not None:
        update_data['allow_anonymous'] = allow_anonymous
    if require_login is not None:
        update_data['require_login'] = require_login
    if sort_order is not None:
        update_data['sort_order'] = sort_order
    
    # 执行更新
    result = Questionnaire.query.filter_by(id=id).update(update_data)
    if not result:
        return fail_api(msg="更新失败")
    
    db.session.commit()
    return success_api(msg="更新成功")


@bp.delete("/remove/<int:_id>")
@authorize("system:questionnaire:remove", log=True)
def remove(_id):
    # 先删除相关的问卷回答
    QuestionnaireResponse.query.filter_by(questionnaire_id=_id).delete()
    # 再删除问卷本身
    d = Questionnaire.query.filter_by(id=_id).delete()
    if not d:
        return fail_api(msg="删除失败")
    db.session.commit()
    return success_api(msg="删除成功")


# 问题管理相关路由
@bp.get("/question/add/<int:questionnaire_id>")
@authorize("system:questionnaire:edit", log=True)
def question_add(questionnaire_id):
    """添加问题页面"""
    questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
    return render_template("system/questionnaire/question_edit.html", questionnaire=questionnaire)


@bp.get("/question/edit/<int:question_id>")
@authorize("system:questionnaire:edit", log=True)
def question_edit(question_id):
    """编辑问题页面"""
    question = curd.get_one_by_id(Question, question_id)
    return render_template("system/questionnaire/question_edit.html", question=question)


@bp.post("/question/save")
@authorize("system:questionnaire:edit", log=True)
def question_save():
    """保存问题"""
    data = request.get_json()
    
    questionnaire_id = data.get('questionnaire_id')
    title = data.get('title')
    description = data.get('description', '')
    question_type = data.get('question_type')
    is_required = data.get('is_required', False)
    sort_order = data.get('sort_order', 0)
    options = data.get('options', [])
    
    if not all([questionnaire_id, title, question_type]):
        return fail_api(msg="请填写完整信息")
    
    # 创建问题
    question = Question(
        questionnaire_id=questionnaire_id,
        title=title,
        description=description,
        question_type=question_type,
        is_required=is_required,
        sort_order=sort_order
    )
    
    db.session.add(question)
    db.session.flush()  # 获取问题ID
    
    # 如果是选择题，添加选项
    if question_type in ['single_choice', 'multiple_choice'] and options:
        for i, option_data in enumerate(options):
            option = QuestionOption(
                question_id=question.id,
                option_text=option_data.get('text', ''),
                option_value=option_data.get('value', ''),
                sort_order=i,
                is_other=option_data.get('is_other', False),
                is_correct=option_data.get('is_correct', False)
            )
            db.session.add(option)
    
    db.session.commit()
    return success_api(msg="保存成功")


@bp.put("/question/update")
def question_update():
    """更新问题"""
    data = request.get_json()
    
    question_id = data.get('id')
    title = data.get('title')
    description = data.get('description', '')
    question_type = data.get('question_type')
    is_required = data.get('is_required', False)
    sort_order = data.get('sort_order', 0)
    options = data.get('options', [])
    
    if not all([question_id, title, question_type]):
        return fail_api(msg="请填写完整信息")
    
    question = Question.query.get(question_id)
    if not question:
        return fail_api(msg="问题不存在")
    
    # 更新问题信息
    question.title = title
    question.description = description
    question.question_type = question_type
    question.is_required = is_required
    question.sort_order = sort_order
    
    # 删除原有选项
    QuestionOption.query.filter_by(question_id=question_id).delete()
    
    # 如果是选择题，添加新选项
    if question_type in ['single_choice', 'multiple_choice'] and options:
        for i, option_data in enumerate(options):
            option = QuestionOption(
                question_id=question_id,
                option_text=option_data.get('text', ''),
                option_value=option_data.get('value', ''),
                sort_order=i,
                is_other=option_data.get('is_other', False),
                is_correct=option_data.get('is_correct', False)
            )
            db.session.add(option)
    
    db.session.commit()
    return success_api(msg="更新成功")


@bp.delete("/question/delete/<int:question_id>")
@authorize("system:questionnaire:edit", log=True)
def question_delete(question_id):
    """删除问题"""
    # 先删除问题选项
    QuestionOption.query.filter_by(question_id=question_id).delete()
    # 删除问题
    result = Question.query.filter_by(id=question_id).delete()
    if not result:
        return fail_api(msg="删除失败")
    
    db.session.commit()
    return success_api(msg="删除成功")


@bp.get("/detail/<int:questionnaire_id>")
def detail(questionnaire_id):
    """根据问卷ID获取问卷详情"""
    questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
    if not questionnaire:
        return fail_api(msg="问卷不存在")
    
    questionnaire_data = {
        'id': questionnaire.id,
        'title': questionnaire.title,
        'description': questionnaire.description,
        'questionnaire_type': questionnaire.questionnaire_type,
        'type_text': questionnaire.type_text,
        'status': questionnaire.status,
        'status_text': questionnaire.status_text,
        'start_time': questionnaire.start_time.strftime('%Y-%m-%d %H:%M:%S') if questionnaire.start_time else None,
        'end_time': questionnaire.end_time.strftime('%Y-%m-%d %H:%M:%S') if questionnaire.end_time else None,
        'max_responses': questionnaire.max_responses,
        'allow_anonymous': questionnaire.allow_anonymous,
        'require_login': questionnaire.require_login,
        'sort_order': questionnaire.sort_order,
        'response_count': questionnaire.response_count,
        'question_count': questionnaire.question_count,
        'create_at': questionnaire.create_at,
        'update_at': questionnaire.update_at,
    }
    
    return jsonify(success=True, msg="获取成功", data=questionnaire_data)


@bp.get("/questions/<int:questionnaire_id>")
def questions(questionnaire_id):
    """根据问卷ID获取问题列表"""
    questions = Question.query.filter_by(questionnaire_id=questionnaire_id).order_by(Question.sort_order).all()
    
    question_list = []
    for question in questions:
        question_data = {
            'id': question.id,
            'title': question.title,
            'description': question.description,
            'question_type': question.question_type,
            'type_text': question.type_text,
            'is_required': question.is_required,
            'sort_order': question.sort_order,
            'options': []
        }
        
        # 如果是选择题，获取选项
        if question.has_options:
            options = question.get_options_list()
            question_data['options'] = [{
                'id': option.id,
                'text': option.option_text,
                'value': option.option_value,
                'is_other': option.is_other,
                'is_correct': option.is_correct
            } for option in options]
        
        question_list.append(question_data)
    
    return jsonify(success=True, msg="获取成功", data=question_list)


@bp.get("/question/detail/<int:question_id>")
def question_detail(question_id):
    """根据问题ID获取问题详情"""
    question = curd.get_one_by_id(Question, question_id)
    if not question:
        return fail_api(msg="问题不存在")
    
    question_data = {
        'id': question.id,
        'questionnaire_id': question.questionnaire_id,
        'title': question.title,
        'description': question.description,
        'question_type': question.question_type,
        'type_text': question.type_text,
        'is_required': question.is_required,
        'sort_order': question.sort_order,
        'options': []
    }
    
    # 如果是选择题，获取选项
    if question.has_options:
        options = question.get_options_list()
        question_data['options'] = [{
            'id': option.id,
            'text': option.option_text,
            'value': option.option_value,
            'is_other': option.is_other,
            'is_correct': option.is_correct
        } for option in options]
    
    return jsonify(success=True, msg="获取成功", data=question_data)


@bp.get("/question/data/<int:questionnaire_id>")
@authorize("system:questionnaire:data", log=True)
def question_data(questionnaire_id):
    """获取问卷的问题列表"""
    questions = Question.query.filter_by(questionnaire_id=questionnaire_id).order_by(Question.sort_order).all()
    
    question_list = []
    for question in questions:
        question_data = {
            'id': question.id,
            'title': question.title,
            'description': question.description,
            'question_type': question.question_type,
            'type_text': question.type_text,
            'is_required': question.is_required,
            'sort_order': question.sort_order,
            'options': []
        }
        
        # 如果是选择题，获取选项
        if question.has_options:
            options = question.get_options_list()
            question_data['options'] = [{
                'id': option.id,
                'text': option.option_text,
                'value': option.option_value,
                'is_other': option.is_other,
                'is_correct': option.is_correct
            } for option in options]
        
        question_list.append(question_data)
    
    return success_api(data=question_list)
