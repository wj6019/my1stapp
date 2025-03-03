from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 初始化 Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 用户数据库文件路径
USER_DB_FILE = 'users.json'

# 加载用户数据库
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

# 保存用户数据库
def save_users(users_db):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users_db, f)

# 用户类
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# 加载用户回调函数
@login_manager.user_loader
def load_user(user_id):
    users_db = load_users()
    for username, user_data in users_db.items():
        if user_data["id"] == int(user_id):
            return User(user_id)
    return None

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users_db = load_users()
        user_data = users_db.get(username)
        if user_data and check_password_hash(user_data["password"], password):
            user = User(user_data["id"])
            login_user(user)
            flash(f"欢迎 {username} 登录系统！")
            return redirect(url_for('index'))
        else:
            flash("用户名或密码错误！")
    return render_template('login.html')

# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users_db = load_users()
        if username in users_db:
            flash("用户名已存在！")
            return redirect(url_for('register'))
        # 生成新的用户 ID
        new_id = max([user_data["id"] for user_data in users_db.values()], default=0) + 1
        # 保存新用户
        users_db[username] = {
            "password": generate_password_hash(password),
            "id": new_id
        }
        save_users(users_db)
        flash(f"用户 {username} 注册成功！请登录。")
        return redirect(url_for('login'))
    return render_template('register.html')

# 注销
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("您已成功注销！")
    return redirect(url_for('login'))

# 主页
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # 检查是否有文件上传
        if 'balance_file' not in request.files or 'bill_file' not in request.files:
            flash('请上传两个文件：账户余额文件和电费账单文件。')
            return redirect(request.url)
        balance_file = request.files['balance_file']
        bill_file = request.files['bill_file']
        # 如果用户没有选择文件，浏览器会提交一个空文件
        if balance_file.filename == '' or bill_file.filename == '':
            flash('请选择文件。')
            return redirect(request.url)
        # 保存上传的文件到用户的专属目录
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        balance_path = os.path.join(user_folder, balance_file.filename)
        bill_path = os.path.join(user_folder, bill_file.filename)
        balance_file.save(balance_path)
        bill_file.save(bill_path)
        # 调用扣款逻辑
        results_df = process_payments(balance_path, bill_path)
        # 返回结果给前端
        return render_template('index.html', results=results_df.to_dict('records'))
    return render_template('index.html')

# 扣款逻辑
def process_payments(balance_path, bill_path):
    # 读取电费账单和账户余额文件
    electricity_bills = pd.read_excel(bill_path)
    account_balances = pd.read_excel(balance_path)
    # 将账户余额列转换为float
    account_balances['账户余额'] = account_balances['账户余额'].astype(float)
    # 确保金额为两位小数
    electricity_bills['电费金额'] = electricity_bills['电费金额'].round(2)
    account_balances['账户余额'] = account_balances['账户余额'].round(2)
    # 创建一个列表，存储扣款结果
    results = []
    # 遍历电费账单，匹配账户余额并进行扣款
    for _, bill in electricity_bills.iterrows():
        user_id = bill['用户ID']
        bill_amount = bill['电费金额']
        # 查找对应的账户余额
        account = account_balances[account_balances['用户ID'] == user_id]
        if not account.empty:
            account_index = account.index[0]
            balance = account['账户余额'].values[0]
            if balance >= bill_amount:
                # 扣除电费
                account_balances.at[account_index, '账户余额'] = round(balance - bill_amount, 2)
                results.append({'用户ID': user_id, '电费金额': bill_amount, '扣款状态': '成功', '剩余余额': round(balance - bill_amount, 2)})
            else:
                results.append({'用户ID': user_id, '电费金额': bill_amount, '扣款状态': '余额不足', '剩余余额': balance})
        else:
            results.append({'用户ID': user_id, '电费金额': bill_amount, '扣款状态': '账户不存在', '剩余余额': None})
    # 将扣款结果转换为DataFrame
    return pd.DataFrame(results)

if __name__ == '__main__':
    app.run(debug=True)