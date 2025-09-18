from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import func, and_
from applications.models.user_notice import UserNotice, UserNoticeConfirm
from applications.models.questionnaire import Questionnaire
from applications.models.questionnaire_response import QuestionnaireResponse
from applications.extensions import db
import datetime

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.get("/stats")
@login_required
def get_dashboard_stats():
    """获取首页统计数据"""
    try:

        # 问卷统计
        questionnaire_stats = get_questionnaire_stats()

        # 今日统计
        today_stats = get_today_stats()

        return jsonify(
            {
                "code": 0,
                "msg": "成功",
                "data": {
                    "questionnaire_stats": {
                        "trend_7days": questionnaire_stats["week_trend"],
                        "trend_30days": get_monthly_trend(),  # 添加30天趋势
                    },
                    "today_stats": {
                        "notice_confirmations": today_stats["notice_confirmations"],
                        "questionnaire_responses": today_stats[
                            "questionnaire_responses"
                        ],
                        "total_questionnaires": questionnaire_stats[
                            "total_questionnaires"
                        ],
                        "completion_rate": questionnaire_stats["completion_rate"],
                    },
                },
            }
        )
    except Exception as e:
        return jsonify({"code": 1, "msg": f"获取统计数据失败: {str(e)}"}), 500


def get_notice_stats():
    """获取用户须知统计数据"""
    # 总须知数
    total_notices = UserNotice.query.filter_by(status=1).count()

    # 已确认的须知数（去重）
    confirmed_notices = db.session.query(UserNoticeConfirm.notice_id).distinct().count()

    # 总确认次数
    total_confirmations = UserNoticeConfirm.query.filter_by(status=1).count()

    # 今日确认次数
    today = datetime.date.today()
    today_confirmations = UserNoticeConfirm.query.filter(
        and_(
            UserNoticeConfirm.status == 1,
            func.date(UserNoticeConfirm.create_at) == today,
        )
    ).count()

    # 最近7天确认趋势
    week_trend = []
    for i in range(7):
        date = today - datetime.timedelta(days=i)
        count = UserNoticeConfirm.query.filter(
            and_(
                UserNoticeConfirm.status == 1,
                func.date(UserNoticeConfirm.create_at) == date,
            )
        ).count()
        week_trend.append({"date": date.strftime("%m-%d"), "count": count})

    return {
        "total_notices": total_notices,
        "confirmed_notices": confirmed_notices,
        "total_confirmations": total_confirmations,
        "today_confirmations": today_confirmations,
        "week_trend": list(reversed(week_trend)),
    }


def get_questionnaire_stats():
    """获取问卷统计数据"""
    # 总问卷数
    total_questionnaires = Questionnaire.query.filter_by(status=1).count()

    # 总回答数
    total_responses = QuestionnaireResponse.query.count()

    # 已完成回答数
    completed_responses = QuestionnaireResponse.query.filter_by(status=1).count()

    # 进行中回答数
    in_progress_responses = QuestionnaireResponse.query.filter_by(status=0).count()

    # 今日回答数
    today = datetime.date.today()
    today_responses = QuestionnaireResponse.query.filter(
        func.date(QuestionnaireResponse.start_time) == today
    ).count()

    # 完成率
    completion_rate = (
        round((completed_responses / total_responses * 100), 2)
        if total_responses > 0
        else 0
    )

    # 最近7天回答趋势
    week_trend = []
    for i in range(7):
        date = today - datetime.timedelta(days=i)
        responses = QuestionnaireResponse.query.filter(
            func.date(QuestionnaireResponse.start_time) == date
        ).count()
        week_trend.append({"date": date.strftime("%m-%d"), "responses": responses})

    return {
        "total_questionnaires": total_questionnaires,
        "total_responses": total_responses,
        "completed_responses": completed_responses,
        "in_progress_responses": in_progress_responses,
        "today_responses": today_responses,
        "completion_rate": completion_rate,
        "week_trend": list(reversed(week_trend)),
    }


def get_today_stats():
    """获取今日统计数据"""
    today = datetime.date.today()

    # 今日须知确认数
    today_notice_confirmations = UserNoticeConfirm.query.filter(
        and_(
            UserNoticeConfirm.status == 1,
            func.date(UserNoticeConfirm.create_at) == today,
        )
    ).count()

    # 今日问卷回答数
    today_questionnaire_responses = QuestionnaireResponse.query.filter(
        func.date(QuestionnaireResponse.start_time) == today
    ).count()

    # 今日完成的问卷数
    today_completed_responses = QuestionnaireResponse.query.filter(
        and_(
            QuestionnaireResponse.status == 1,
            func.date(QuestionnaireResponse.submit_time) == today,
        )
    ).count()

    return {
        "notice_confirmations": today_notice_confirmations,
        "questionnaire_responses": today_questionnaire_responses,
        "completed_responses": today_completed_responses,
    }


def get_monthly_trend():
    """获取30天问卷趋势数据"""
    try:
        trend_data = []
        today = datetime.date.today()
        
        # 获取最近30天的问卷回答数据
        for i in range(30):
            date = today - datetime.timedelta(days=29 - i)
            
            # 查询当天的问卷回答数量（包括进行中和已完成的）
            responses_count = QuestionnaireResponse.query.filter(
                func.date(QuestionnaireResponse.start_time) == date
            ).count()
            
            trend_data.append({
                "date": date.strftime("%m-%d"), 
                "responses": responses_count
            })

        return trend_data
    except Exception as e:
        # 如果查询失败，返回空列表而不是模拟数据
        return []
