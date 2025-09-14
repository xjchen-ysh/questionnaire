from flask_marshmallow.sqla import SQLAlchemyAutoSchema

from applications.models import (
    Questionnaire,
    Question,
    QuestionOption,
    QuestionnaireResponse,
    QuestionAnswer,
)


class QuestionnaireOutSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Questionnaire  # table = models.Album.__table__
        # include_relationships = True  # 输出模型对象时同时对外键，是否也一并进行处理
        include_fk = True  # 序列化阶段是否也一并返回主键
        # fields= ["id","name"] # 启动的字段列表
        # exclude = ["id","name"] # 排除字段列表


class QuestionOutSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Question  # table = models.Album.__table__
        # include_relationships = True  # 输出模型对象时同时对外键，是否也一并进行处理
        include_fk = True  # 序列化阶段是否也一并返回主键
        # fields= ["id","name"] # 启动的字段列表
        # exclude = ["id","name"] # 排除字段列表


class QuestionOptionOutSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionOption  # table = models.Album.__table__
        # include_relationships = True  # 输出模型对象时同时对外键，是否也一并进行处理
        include_fk = True  # 序列化阶段是否也一并返回主键
        # fields= ["id","name"] # 启动的字段列表
        # exclude = ["id","name"] # 排除字段列表


class QuestionnaireResponseOutSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionnaireResponse  # table = models.Album.__table__
        # include_relationships = True  # 输出模型对象时同时对外键，是否也一并进行处理
        include_fk = True  # 序列化阶段是否也一并返回主键
        # fields= ["id","name"] # 启动的字段列表
        # exclude = ["id","name"] # 排除字段列表


class QuestionAnswerOutSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionAnswer  # table = models.Album.__table__
        # include_relationships = True  # 输出模型对象时同时对外键，是否也一并进行处理
        include_fk = True  # 序列化阶段是否也一并返回主键
        # fields= ["id","name"] # 启动的字段列表
        # exclude = ["id","name"] # 排除字段列表
