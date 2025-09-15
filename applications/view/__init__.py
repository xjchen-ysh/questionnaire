from applications.view.system import register_system_bps
from applications.view.plugin import register_plugin_views
from applications.view.frontend import frontend_bp


def init_bps(app):
    register_system_bps(app)
    register_plugin_views(app)
    # 注册前端用户API蓝图
    app.register_blueprint(frontend_bp)
