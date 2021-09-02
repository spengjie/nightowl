from flask import Blueprint


bp = Blueprint('api', __name__)


@bp.route('')
def api_root():
    api_list = '''
<pre>
</pre>
    '''
    return api_list, 200
