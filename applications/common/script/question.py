import datetime
from flask.cli import AppGroup
from applications.extensions import db
from applications.models.questionnaire import Questionnaire, Question, QuestionOption
from applications.models.questionnaire_response import QuestionnaireResponse, QuestionAnswer

question_cli = AppGroup("question")


def init_questionnaire_data():
    """初始化问卷模块数据"""
    print("开始初始化问卷模块数据...")
    
    # 创建示例问卷1：用户满意度调查
    questionnaire1 = Questionnaire(
        title='用户满意度调查',
        description='为了更好地为您服务，请花几分钟时间填写这份满意度调查问卷。您的反馈对我们非常重要！',
        questionnaire_type='survey',
        status=1,
        allow_anonymous=True,
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(days=30)
    )
    db.session.add(questionnaire1)
    db.session.commit()
    
    # 为问卷1创建问题
    questions1 = [
        {
            'title': '您对我们的服务总体满意度如何？',
            'question_type': 'single_choice',
            'is_required': True,
            'sort_order': 1,
            'options': [
                {'option_text': '非常满意', 'sort_order': 1},
                {'option_text': '满意', 'sort_order': 2},
                {'option_text': '一般', 'sort_order': 3},
                {'option_text': '不满意', 'sort_order': 4},
                {'option_text': '非常不满意', 'sort_order': 5}
            ]
        },
        {
            'title': '您认为我们需要改进的方面有哪些？（多选）',
            'question_type': 'multiple_choice',
            'is_required': False,
            'sort_order': 2,
            'options': [
                {'option_text': '服务态度', 'sort_order': 1},
                {'option_text': '响应速度', 'sort_order': 2},
                {'option_text': '产品质量', 'sort_order': 3},
                {'option_text': '价格合理性', 'sort_order': 4},
                {'option_text': '其他', 'sort_order': 5, 'is_other': True, 'allow_input': True}
            ]
        },
        {
            'title': '请对我们的服务进行评分（1-5分）：',
            'question_type': 'rating',
            'is_required': True,
            'sort_order': 3,
            'config': {'min_rating': 1, 'max_rating': 5}
        },
        {
            'title': '请留下您的宝贵建议：',
            'question_type': 'textarea',
            'is_required': False,
            'sort_order': 4
        }
    ]
    
    for question_data in questions1:
        options_data = question_data.pop('options', [])
        question = Question(
            questionnaire_id=questionnaire1.id,
            **question_data
        )
        db.session.add(question)
        db.session.commit()
        
        # 创建选项
        for option_data in options_data:
            option = QuestionOption(
                question_id=question.id,
                **option_data
            )
            db.session.add(option)
    
    # 创建示例问卷2：产品反馈调查
    questionnaire2 = Questionnaire(
        title='产品反馈调查',
        description='我们想了解您对我们产品的使用体验，您的反馈将帮助我们改进产品。',
        questionnaire_type='feedback',
        status=1,
        allow_anonymous=False,
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now() + datetime.timedelta(days=60)
    )
    db.session.add(questionnaire2)
    db.session.commit()
    
    # 为问卷2创建问题
    questions2 = [
        {
            'title': '您的姓名：',
            'question_type': 'text',
            'is_required': True,
            'sort_order': 1
        },
        {
            'title': '您使用我们产品多长时间了？',
            'question_type': 'single_choice',
            'is_required': True,
            'sort_order': 2,
            'options': [
                {'option_text': '不到1个月', 'sort_order': 1},
                {'option_text': '1-3个月', 'sort_order': 2},
                {'option_text': '3-6个月', 'sort_order': 3},
                {'option_text': '6个月-1年', 'sort_order': 4},
                {'option_text': '1年以上', 'sort_order': 5}
            ]
        },
        {
            'title': '您最常使用的功能有哪些？（多选）',
            'question_type': 'multiple_choice',
            'is_required': False,
            'sort_order': 3,
            'options': [
                {'option_text': '数据分析', 'sort_order': 1},
                {'option_text': '报表生成', 'sort_order': 2},
                {'option_text': '用户管理', 'sort_order': 3},
                {'option_text': '系统设置', 'sort_order': 4},
                {'option_text': '导入导出', 'sort_order': 5}
            ]
        },
        {
            'title': '您希望我们添加什么新功能？',
            'question_type': 'textarea',
            'is_required': False,
            'sort_order': 4
        }
    ]
    
    for question_data in questions2:
        options_data = question_data.pop('options', [])
        question = Question(
            questionnaire_id=questionnaire2.id,
            **question_data
        )
        db.session.add(question)
        db.session.commit()
        
        # 创建选项
        for option_data in options_data:
            option = QuestionOption(
                question_id=question.id,
                **option_data
            )
            db.session.add(option)
    
    # 创建一些示例回答数据
    # 为问卷1创建回答
    response1 = QuestionnaireResponse(
        questionnaire_id=questionnaire1.id,
        ip_address='192.168.1.100',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        status=1,
        submit_time=datetime.datetime.now()
    )
    db.session.add(response1)
    db.session.commit()
    
    # 为回答1添加答案
    q1_questions = Question.query.filter_by(questionnaire_id=questionnaire1.id).order_by(Question.sort_order).all()
    if len(q1_questions) >= 4:
        # 第一题：单选
        answer1 = QuestionAnswer(
            response_id=response1.id,
            question_id=q1_questions[0].id,
            answer_option_ids=str(q1_questions[0].options.first().id)
        )
        db.session.add(answer1)
        
        # 第二题：多选
        options = q1_questions[1].options.limit(3).all()
        option_ids = [str(opt.id) for opt in options]
        answer2 = QuestionAnswer(
            response_id=response1.id,
            question_id=q1_questions[1].id,
            answer_option_ids=','.join(option_ids)
        )
        db.session.add(answer2)
        
        # 第三题：评分
        answer3 = QuestionAnswer(
            response_id=response1.id,
            question_id=q1_questions[2].id,
            answer_value='8'
        )
        db.session.add(answer3)
        
        # 第四题：文本
        answer4 = QuestionAnswer(
            response_id=response1.id,
            question_id=q1_questions[3].id,
            answer_text='希望能够增加更多的自定义选项，界面也可以更加美观一些。'
        )
        db.session.add(answer4)
    
    db.session.commit()
    print("问卷模块数据初始化完成！")
    print(f"创建了 {Questionnaire.query.count()} 个问卷")
    print(f"创建了 {Question.query.count()} 个问题")
    print(f"创建了 {QuestionOption.query.count()} 个选项")
    print(f"创建了 {QuestionnaireResponse.query.count()} 个回答")
    print(f"创建了 {QuestionAnswer.query.count()} 个答案")


def clear_questionnaire_data():
    """清空问卷模块数据"""
    print("开始清空问卷模块数据...")
    
    # 按照外键依赖关系的逆序删除
    QuestionAnswer.query.delete()
    QuestionnaireResponse.query.delete()
    QuestionOption.query.delete()
    Question.query.delete()
    Questionnaire.query.delete()
    
    db.session.commit()
    print("问卷模块数据清空完成！")

def clear_questionnaire_answer_data():
    """清空问卷模块所有回答数据"""
    print("开始清空问卷模块所有回答数据...")
    QuestionAnswer.query.delete()
    QuestionnaireResponse.query.delete()
    db.session.commit()
    print("问卷模块所有回答数据清空完成！")


@question_cli.command("init")
def init_db():
    """初始化问卷模块测试数据"""
    init_questionnaire_data()

@question_cli.command("clear")
def clear_db():
    """清空问卷模块所有数据"""
    clear_questionnaire_data()

@question_cli.command("clear_answer")
def clear_answer_db():
    """清空问卷模块所有回答数据"""
    clear_questionnaire_answer_data()


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'init':
            init_questionnaire_data()
        elif sys.argv[1] == 'clear':
            clear_questionnaire_data()
        else:
            print("使用方法: python question.py [init|clear]")
            print("  init  - 初始化问卷模块测试数据")
            print("  clear - 清空问卷模块所有数据")
    else:
        print("使用方法: python question.py [init|clear]")
        print("  init  - 初始化问卷模块测试数据")
        print("  clear - 清空问卷模块所有数据")
    