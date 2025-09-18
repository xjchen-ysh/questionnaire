from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('index', __name__, url_prefix='/')


# 首页
@bp.get('/')
@login_required
def index():
    user = current_user
    return render_template('system/index.html', user=user)


# 控制台页面
@bp.get('/system/console')
@login_required
def console():
    return render_template('system/console/console.html')


