from venv import logger
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
from applications.schemas import (
    QuestionnaireOutSchema,
    QuestionOutSchema,
    QuestionOptionOutSchema,
)
from plugins.realip import get_user_ip

bp = Blueprint("questionnaire", __name__, url_prefix="/questionnaire")


@bp.get("/")
@authorize("system:questionnaire:main", log=True)
def main():
    return render_template("system/questionnaire/main.html")


@bp.get("/data")
@authorize("system:questionnaire:main", log=True)
def data():
    questionnaire_name = str_escape(request.args.get("questionnaire_name", type=str))

    filters = []
    if questionnaire_name:
        filters.append(Questionnaire.title.contains(questionnaire_name))
    query = (
        Questionnaire.query.filter(*filters)
        .order_by(Questionnaire.sort_order)
        .layui_paginate()
    )

    return table_api(
        data=[
            {
                "id": questionnaire.id,  #
                "title": questionnaire.title,
                "description": questionnaire.description,
                "questionnaire_type": questionnaire.questionnaire_type,
                "type_text": questionnaire.type_text,
                "status": questionnaire.status,
                "status_text": questionnaire.status_text,
                "start_time": (
                    questionnaire.start_time.strftime("%Y-%m-%d %H:%M:%S")
                    if questionnaire.start_time
                    else None
                ),
                "end_time": (
                    questionnaire.end_time.strftime("%Y-%m-%d %H:%M:%S")
                    if questionnaire.end_time
                    else None
                ),
                "max_responses": questionnaire.max_responses,
                "allow_anonymous": questionnaire.allow_anonymous,
                "require_login": questionnaire.require_login,
                "sort_order": questionnaire.sort_order,
                "response_count": questionnaire.response_count,
                "question_count": questionnaire.question_count,
                "create_at": questionnaire.create_at,
                "update_at": questionnaire.update_at,
            }
            for questionnaire in query.items
        ],
        count=query.total,
    )


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
    start_time = req_json.get("start_time")
    end_time = req_json.get("end_time")

    start_time_obj = None
    end_time_obj = None

    if start_time:
        try:
            start_time_obj = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="开始时间格式错误")

    if end_time:
        try:
            end_time_obj = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="结束时间格式错误")

    questionnaire = Questionnaire(
        title=str_escape(req_json.get("title")),
        description=str_escape(req_json.get("description")),
        questionnaire_type=str_escape(req_json.get("questionnaire_type")),
        status=req_json.get("status"),
        start_time=start_time_obj,
        end_time=end_time_obj,
        max_responses=req_json.get("max_responses") or 0,
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
    return render_template(
        "system/questionnaire/edit.html", questionnaire=questionnaire
    )


@bp.get("/design/<int:id>")
@authorize("system:questionnaire:edit", log=True)
def design(id):
    questionnaire = curd.get_one_by_id(Questionnaire, id)
    return render_template(
        "system/questionnaire/design.html", questionnaire=questionnaire
    )


# 发布问卷
@bp.post("/publish/<int:questionnaire_id>")
@authorize("system:questionnaire:edit", log=True)
def publish(questionnaire_id):
    """发布问卷接口"""
    if not questionnaire_id:
        return fail_api(msg="问卷ID不能为空")

    # 查询问卷信息
    questionnaire = Questionnaire.query.get(questionnaire_id)
    if not questionnaire:
        return fail_api(msg="问卷不存在")

    # 检查问卷是否已经发布
    if questionnaire.status == 1:
        return fail_api(msg="问卷已经发布，无需重复发布")

    # 验证问卷是否可以发布
    # 1. 检查问卷是否有问题
    question_count = questionnaire.questions.count()
    if question_count == 0:
        return fail_api(msg="问卷至少需要包含一个问题才能发布")

    # 2. 检查所有问题是否配置完整
    for question in questionnaire.questions:
        # 选择题必须有选项
        if question.question_type in ["single_choice", "multiple_choice"]:
            option_count = question.options.count()
            if option_count < 2:
                return fail_api(msg=f'选择题"{question.title}"至少需要2个选项')

    # 3. 检查结束时间必须晚于开始时间
    current_time = datetime.now()
    if questionnaire.start_time and questionnaire.end_time:
        if questionnaire.end_time <= questionnaire.start_time:
            return fail_api(msg="结束时间必须晚于开始时间")

    try:
        # 更新问卷状态为发布状态
        questionnaire.status = 1  # 1表示发布状态
        questionnaire.is_published = True
        questionnaire.update_at = current_time

        db.session.commit()
        return success_api(msg="问卷发布成功")

    except Exception as e:
        db.session.rollback()
        return fail_api(msg=f"发布失败：{str(e)}")


@bp.put("/update")
@authorize("system:questionnaire:edit", log=True)
def update():
    req_json = request.get_json(force=True)
    id = str_escape(req_json.get("id"))
    title = str_escape(req_json.get("title"))
    description = str_escape(req_json.get("description"))
    questionnaire_type = str_escape(req_json.get("questionnaire_type"))
    status = req_json.get("status")
    start_time = req_json.get("start_time")
    end_time = req_json.get("end_time")
    max_responses = req_json.get("max_responses") or 0
    allow_anonymous = req_json.get("allow_anonymous")
    require_login = req_json.get("require_login")
    sort_order = req_json.get("sort_order")

    # 构建更新数据字典
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if questionnaire_type is not None:
        update_data["questionnaire_type"] = questionnaire_type
    if status is not None:
        update_data["status"] = status
    if start_time is not None:
        try:
            # 将字符串时间转换为datetime对象
            update_data["start_time"] = datetime.strptime(
                start_time, "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, TypeError):
            return fail_api(msg="开始时间格式错误")
    if end_time is not None:
        try:
            # 将字符串时间转换为datetime对象
            update_data["end_time"] = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return fail_api(msg="结束时间格式错误")
    if max_responses is not None:
        update_data["max_responses"] = max_responses
    if allow_anonymous is not None:
        update_data["allow_anonymous"] = allow_anonymous
    if require_login is not None:
        update_data["require_login"] = require_login
    if sort_order is not None:
        update_data["sort_order"] = sort_order

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
    return render_template(
        "system/questionnaire/question_edit.html", questionnaire=questionnaire
    )


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

    questionnaire_id = data.get("questionnaire_id")
    title = data.get("title")
    description = data.get("description", "")
    question_type = data.get("question_type")
    is_required = data.get("is_required", False)
    sort_order = data.get("sort_order", 0)
    options = data.get("options", [])

    if not all([questionnaire_id, title, question_type]):
        return fail_api(msg="请填写完整信息")

    # 设置问题配置
    config = None
    if question_type == "rating":
        # 评分题默认配置
        config = {"max_rating": 5, "min_rating": 1}

    # 创建问题
    question = Question(
        questionnaire_id=questionnaire_id,
        title=title,
        description=description,
        question_type=question_type,
        is_required=is_required,
        sort_order=sort_order,
        config=config,
    )

    db.session.add(question)
    db.session.flush()  # 获取问题ID

    # 如果是选择题，添加选项
    if question_type in ["single_choice", "multiple_choice"] and options:
        for i, option_data in enumerate(options):
            option = QuestionOption(
                question_id=question.id,
                option_text=option_data.get("text", ""),
                option_value=option_data.get("value", ""),
                sort_order=i,
                is_other=option_data.get("is_other", False),
                is_correct=option_data.get("is_correct", False),
                allow_input=option_data.get("allow_input", False),  # 是否允许用户输入
            )
            db.session.add(option)

    db.session.commit()
    return success_api(msg="保存成功")


@bp.put("/question/update")
def question_update():
    """更新问题"""
    data = request.get_json()

    question_id = data.get("id")
    title = data.get("title")
    description = data.get("description", "")
    question_type = data.get("question_type")
    is_required = data.get("is_required", False)
    sort_order = data.get("sort_order", 0)
    options = data.get("options", [])

    if not all([question_id, title, question_type]):
        return fail_api(msg="请填写完整信息")

    question = Question.query.get(question_id)
    if not question:
        return fail_api(msg="问题不存在")

    # 设置问题配置
    config = None
    if question_type == "rating":
        # 评分题默认配置
        config = {"max_rating": 5, "min_rating": 1}

    # 更新问题信息
    question.title = title
    question.description = description
    question.question_type = question_type
    question.is_required = is_required
    question.sort_order = sort_order
    question.config = config

    # 删除原有选项
    QuestionOption.query.filter_by(question_id=question_id).delete()

    # 如果是选择题，添加新选项
    if question_type in ["single_choice", "multiple_choice"] and options:
        for i, option_data in enumerate(options):
            option = QuestionOption(
                question_id=question_id,
                option_text=option_data.get("text", ""),
                option_value=option_data.get("value", ""),
                sort_order=i,
                is_other=option_data.get("is_other", False),
                is_correct=option_data.get("is_correct", False),
                allow_input=option_data.get("allow_input", False),  # 是否允许用户输入
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
        "id": questionnaire.id,
        "title": questionnaire.title,
        "description": questionnaire.description,
        "questionnaire_type": questionnaire.questionnaire_type,
        "type_text": questionnaire.type_text,
        "status": questionnaire.status,
        "status_text": questionnaire.status_text,
        "start_time": (
            questionnaire.start_time.strftime("%Y-%m-%d %H:%M:%S")
            if questionnaire.start_time
            else None
        ),
        "end_time": (
            questionnaire.end_time.strftime("%Y-%m-%d %H:%M:%S")
            if questionnaire.end_time
            else None
        ),
        "max_responses": questionnaire.max_responses,
        "allow_anonymous": questionnaire.allow_anonymous,
        "require_login": questionnaire.require_login,
        "sort_order": questionnaire.sort_order,
        "response_count": questionnaire.response_count,
        "question_count": questionnaire.question_count,
        "create_at": questionnaire.create_at,
        "update_at": questionnaire.update_at,
    }

    return jsonify(success=True, msg="获取成功", data=questionnaire_data)


@bp.get("/questions/<int:questionnaire_id>")
def questions(questionnaire_id):
    """根据问卷ID获取问题列表"""
    questions = (
        Question.query.filter_by(questionnaire_id=questionnaire_id)
        .order_by(Question.sort_order)
        .all()
    )

    question_list = []
    for question in questions:
        question_data = {
            "id": question.id,
            "title": question.title,
            "description": question.description,
            "question_type": question.question_type,
            "type_text": question.type_text,
            "is_required": question.is_required,
            "sort_order": question.sort_order,
            "options": [],
        }

        # 如果是选择题，获取选项
        if question.has_options:
            options = question.get_options_list()
            question_data["options"] = [
                {
                    "id": option.id,
                    "text": option.option_text,
                    "value": option.option_value,
                    "is_other": option.is_other,
                    "is_correct": option.is_correct,
                }
                for option in options
            ]

        question_list.append(question_data)

    return jsonify(success=True, msg="获取成功", data=question_list)


@bp.get("/question/detail/<int:question_id>")
def question_detail(question_id):
    """根据问题ID获取问题详情"""
    question = curd.get_one_by_id(Question, question_id)
    if not question:
        return fail_api(msg="问题不存在")

    question_data = {
        "id": question.id,
        "questionnaire_id": question.questionnaire_id,
        "title": question.title,
        "description": question.description,
        "question_type": question.question_type,
        "type_text": question.type_text,
        "is_required": question.is_required,
        "sort_order": question.sort_order,
        "options": [],
    }

    # 如果是选择题，获取选项
    if question.has_options:
        options = question.get_options_list()
        question_data["options"] = [
            {
                "id": option.id,
                "text": option.option_text,
                "value": option.option_value,
                "is_other": option.is_other,
                "is_correct": option.is_correct,
            }
            for option in options
        ]

    return jsonify(success=True, msg="获取成功", data=question_data)


@bp.get("/question/data/<int:questionnaire_id>")
@authorize("system:questionnaire:main", log=True)
def question_data(questionnaire_id):
    """获取问卷的问题列表"""
    questions = (
        Question.query.filter_by(questionnaire_id=questionnaire_id)
        .order_by(Question.sort_order)
        .all()
    )

    question_list = []
    for question in questions:
        question_data = {
            "id": question.id,
            "title": question.title,
            "description": question.description,
            "question_type": question.question_type,
            "type_text": question.type_text,
            "is_required": question.is_required,
            "sort_order": question.sort_order,
            "options": [],
        }

        # 如果是选择题，获取选项
        if question.has_options:
            options = question.get_options_list()
            question_data["options"] = [
                {
                    "id": option.id,
                    "text": option.option_text,
                    "value": option.option_value,
                    "is_other": option.is_other,
                    "is_correct": option.is_correct,
                }
                for option in options
            ]

        question_list.append(question_data)

    return success_api(data=question_list)


@bp.get("/preview/<int:questionnaire_id>")
def preview(questionnaire_id):
    """问卷预览页面"""
    questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
    if not questionnaire:
        return "问卷不存在", 404

    # 获取问卷的所有问题和选项
    questions = (
        Question.query.filter_by(questionnaire_id=questionnaire_id)
        .order_by(Question.sort_order)
        .all()
    )

    return render_template(
        "system/questionnaire/preview.html",
        questionnaire=questionnaire,
        questions=questions,
    )


@bp.get("/fill/<int:questionnaire_id>")
def fill(questionnaire_id):
    """问卷填写页面（移动端友好）"""
    questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
    if not questionnaire:
        return "问卷不存在", 404
    
    # 检查问卷状态
    if questionnaire.status != 1:
        return "问卷未发布或已关闭", 403
    
    # 检查问卷时间
    current_time = datetime.now()
    if questionnaire.start_time and current_time < questionnaire.start_time:
        return "问卷尚未开始", 403
    
    if questionnaire.end_time and current_time > questionnaire.end_time:
        return "问卷已结束", 403
    
    # 检查回答数量限制
    if questionnaire.max_responses:
        response_count = QuestionnaireResponse.query.filter_by(
            questionnaire_id=questionnaire_id
        ).count()
        if response_count >= questionnaire.max_responses:
            return "问卷回答数量已达上限", 403

    # 获取问卷的所有问题和选项
    questions = (
        Question.query.filter_by(questionnaire_id=questionnaire_id)
        .order_by(Question.sort_order)
        .all()
    )

    return render_template(
        "system/questionnaire/fill.html",
        questionnaire=questionnaire,
        questions=questions,
    )


@bp.post("/submit/<int:questionnaire_id>")
def submit_questionnaire(questionnaire_id):
    """提交问卷答案"""
    try:
        questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
        if not questionnaire:
            return fail_api(msg="问卷不存在")
        
        # 检查问卷状态
        if questionnaire.status != 1:
            return fail_api(msg="问卷未发布或已关闭")
        
        # 检查问卷时间
        current_time = datetime.now()
        if questionnaire.start_time and current_time < questionnaire.start_time:
            return fail_api(msg="问卷尚未开始")
        
        if questionnaire.end_time and current_time > questionnaire.end_time:
            return fail_api(msg="问卷已结束")
        
        # 检查回答数量限制
        if questionnaire.max_responses:
            response_count = QuestionnaireResponse.query.filter_by(
                questionnaire_id=questionnaire_id
            ).count()
            if response_count >= questionnaire.max_responses:
                return fail_api(msg="问卷回答数量已达上限")

        # 获取提交的数据
        data = request.get_json()
        if not data:
            return fail_api(msg="提交数据不能为空")
        
        # 验证手机号
        phone = data.get('phone', '').strip()
        if not phone:
            return fail_api(msg="请填写手机号")
        
        # 简单的手机号格式验证
        import re
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return fail_api(msg="手机号格式不正确")
        
        # 获取姓名（可选）
        name = data.get('name', '').strip()
        
        # 获取问题答案
        answers = data.get('answers', {})
        if not answers:
            return fail_api(msg="请至少回答一个问题")
        
        # 验证必填问题
        questions = Question.query.filter_by(questionnaire_id=questionnaire_id).all()
        for question in questions:
            if question.is_required and str(question.id) not in answers:
                return fail_api(msg=f"问题{question.title}为必填项")
        
        # 创建问卷回答记录
        response = QuestionnaireResponse(
            questionnaire_id=questionnaire_id,
            phone=phone,
            name=name if name else None,  # 保存姓名，如果为空则设为None
            status=1,  # 已完成
            submit_time=current_time,
            ip_address=get_user_ip(request)
        )
        
        db.session.add(response)
        db.session.flush()  # 获取response.id
        
        # 导入QuestionAnswer模型
        from applications.models.questionnaire_response import QuestionAnswer
        
        # 保存每个问题的答案
        for question_id_str, answer_data in answers.items():
            question_id = int(question_id_str)
            
            # 创建答案记录
            answer = QuestionAnswer(
                response_id=response.id,
                question_id=question_id
            )
            
            # 根据答案类型设置相应字段
            if isinstance(answer_data, dict):
                # 处理复杂答案（包含选项和自定义输入）
                if 'options' in answer_data:
                    answer.set_option_ids(answer_data['options'])
                if 'text' in answer_data:
                    answer.answer_text = answer_data['text']
                if 'custom_inputs' in answer_data:
                    answer.option_custom_inputs = answer_data['custom_inputs']
            elif isinstance(answer_data, list):
                # 多选题答案
                answer.set_option_ids(answer_data)
            elif isinstance(answer_data, str):
                # 文本答案
                answer.answer_text = answer_data
            else:
                # 其他类型（如数字）
                answer.answer_value = str(answer_data)
            
            db.session.add(answer)
        
        db.session.commit()
        
        return success_api(msg="提交成功，感谢您的参与！")
        
    except Exception as e:
        db.session.rollback()
        return fail_api(msg=f"提交失败：{str(e)}")


# 问卷填写记录查看相关路由
@bp.get("/responses/<int:questionnaire_id>")
@authorize("system:questionnaire:main", log=True)
def responses(questionnaire_id):
    """问卷填写记录查看页面"""
    questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
    if not questionnaire:
        return "问卷不存在", 404
    
    return render_template(
        "system/questionnaire/response_main.html",
        questionnaire=questionnaire
    )


@bp.get("/response_data/<int:questionnaire_id>")
@authorize("system:questionnaire:main", log=True)
def response_data(questionnaire_id):
    """问卷填写记录数据接口"""
    # 获取查询参数
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    phone = request.args.get('phone', '').strip()
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # 构建查询条件
    query = QuestionnaireResponse.query.filter_by(questionnaire_id=questionnaire_id)
    
    # 手机号筛选
    if phone:
        query = query.filter(QuestionnaireResponse.phone.like(f'%{phone}%'))
    
    # 状态筛选
    if status != '':
        query = query.filter(QuestionnaireResponse.status == int(status))
    
    # 时间范围筛选
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(QuestionnaireResponse.submit_time >= start_datetime)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = query.filter(QuestionnaireResponse.submit_time <= end_datetime)
        except ValueError:
            pass
    
    # 排序
    query = query.order_by(QuestionnaireResponse.submit_time.desc())
    
    # 分页
    total = query.count()
    responses = query.offset((page - 1) * limit).limit(limit).all()
    
    # 格式化数据
    data = []
    for response in responses:
        # 计算用时
        duration = ""
        if response.start_time and response.submit_time:
            delta = response.submit_time - response.start_time
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            duration = f"{minutes}分{seconds}秒"
        
        data.append({
            'id': response.id,
            'phone': response.phone or '',
            'ip_address': response.ip_address or '',
            'user_agent': response.user_agent or '',
            'status': response.status,
            'start_time': response.start_time.strftime('%Y-%m-%d %H:%M:%S') if response.start_time else '',
            'submit_time': response.submit_time.strftime('%Y-%m-%d %H:%M:%S') if response.submit_time else '',
            'duration': duration
        })
    
    return table_api(data=data, count=total)


@bp.get("/response_detail/<int:response_id>")
@authorize("system:questionnaire:main", log=True)
def response_detail(response_id):
    """问卷填写记录详情页面"""
    response = curd.get_one_by_id(QuestionnaireResponse, response_id)
    if not response:
        return "记录不存在", 404
    
    # 获取问卷信息
    questionnaire = curd.get_one_by_id(Questionnaire, response.questionnaire_id)
    
    # 获取所有问题和答案
    from applications.models.questionnaire_response import QuestionAnswer
    questions = Question.query.filter_by(questionnaire_id=response.questionnaire_id).order_by(Question.sort_order).all()
    
    # 获取该回答的所有答案
    answers = QuestionAnswer.query.filter_by(response_id=response.id).all()
    answer_dict = {answer.question_id: answer for answer in answers}
    
    return render_template(
        "system/questionnaire/response_detail.html",
        response=response,
        questionnaire=questionnaire,
        questions=questions,
        answer_dict=answer_dict
    )


@bp.get("/response_export/<int:questionnaire_id>")
@authorize("system:questionnaire:export", log=True)
def response_export(questionnaire_id):
    """导出问卷填写记录"""
    import csv
    import io
    from flask import make_response
    
    questionnaire = curd.get_one_by_id(Questionnaire, questionnaire_id)
    if not questionnaire:
        return "问卷不存在", 404
    
    # 获取查询参数（与response_data相同的筛选逻辑）
    phone = request.args.get('phone', '').strip()
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # 构建查询条件
    query = QuestionnaireResponse.query.filter_by(questionnaire_id=questionnaire_id)
    
    if phone:
        query = query.filter(QuestionnaireResponse.phone.like(f'%{phone}%'))
    
    if status != '':
        query = query.filter(QuestionnaireResponse.status == int(status))
    
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(QuestionnaireResponse.submit_time >= start_datetime)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = query.filter(QuestionnaireResponse.submit_time <= end_datetime)
        except ValueError:
            pass
    
    responses = query.order_by(QuestionnaireResponse.submit_time.desc()).all()
    
    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    headers = ['ID', '手机号', 'IP地址', '状态', '开始时间', '提交时间', '用时']
    writer.writerow(headers)
    
    # 写入数据
    for response in responses:
        # 计算用时
        duration = ""
        if response.start_time and response.submit_time:
            delta = response.submit_time - response.start_time
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            duration = f"{minutes}分{seconds}秒"
        
        row = [
            response.id,
            response.phone or '',
            response.ip_address or '',
            '已完成' if response.status == 1 else '进行中',
            response.start_time.strftime('%Y-%m-%d %H:%M:%S') if response.start_time else '',
            response.submit_time.strftime('%Y-%m-%d %H:%M:%S') if response.submit_time else '',
            duration
        ]
        writer.writerow(row)
    
    # 创建响应
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=questionnaire_{questionnaire_id}_responses.csv'
    
    return response


@bp.get("/response_download/<int:response_id>")
@authorize("system:questionnaire:main", log=True)
def response_download(response_id):
    """下载单个问卷填写记录"""
    import json
    from flask import make_response
    
    response = curd.get_one_by_id(QuestionnaireResponse, response_id)
    if not response:
        return "记录不存在", 404
    
    # 获取问卷和问题信息
    questionnaire = curd.get_one_by_id(Questionnaire, response.questionnaire_id)
    questions = Question.query.filter_by(questionnaire_id=response.questionnaire_id).order_by(Question.sort_order).all()
    
    # 获取答案
    from applications.models.questionnaire_response import QuestionAnswer
    answers = QuestionAnswer.query.filter_by(response_id=response.id).all()
    answer_dict = {answer.question_id: answer for answer in answers}
    
    # 构建导出数据
    export_data = {
        'questionnaire': {
            'id': questionnaire.id,
            'title': questionnaire.title,
            'description': questionnaire.description
        },
        'response': {
            'id': response.id,
            'phone': response.phone,
            'ip_address': response.ip_address,
            'status': '已完成' if response.status == 1 else '进行中',
            'start_time': response.start_time.strftime('%Y-%m-%d %H:%M:%S') if response.start_time else '',
            'submit_time': response.submit_time.strftime('%Y-%m-%d %H:%M:%S') if response.submit_time else ''
        },
        'answers': []
    }
    
    # 添加问题和答案
    for question in questions:
        answer = answer_dict.get(question.id)
        question_data = {
            'question_id': question.id,
            'title': question.title,
            'type': question.question_type,
            'answer': ''
        }
        
        if answer:
            if answer.answer_text:
                question_data['answer'] = answer.answer_text
            elif answer.answer_value:
                question_data['answer'] = answer.answer_value
            elif answer.answer_option_ids:
                # 获取选项文本
                option_ids = answer.get_option_ids()
                options = QuestionOption.query.filter(QuestionOption.id.in_(option_ids)).all()
                question_data['answer'] = ', '.join([opt.option_text for opt in options])
        
        export_data['answers'].append(question_data)
    
    # 创建JSON响应
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    response = make_response(json_str)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=response_{response_id}.json'
    
    return response
