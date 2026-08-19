from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
from datetime import datetime
from flask import flash
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = "ENTER YOUR SECRETKEY HERE"

bcrypt = Bcrypt(app)
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="ENTER YOUR PASSWORD HERE",
        database="expense_tracker"
    )

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = bcrypt.generate_password_hash(
            request.form['password']
        ).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
            (name, email, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('registor.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))

        return "Invalid Login Details"

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template("dashboard.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))




@app.route('/income', methods=['GET', 'POST'])
def income():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    
    if request.method == 'POST' and 'amount' in request.form:
        amount = request.form['amount']
        date = request.form['date']
        description = request.form['description']

        cursor.execute(
            "INSERT INTO income (user_id, amount, income_date, description) VALUES (%s, %s, %s, %s)",
            (user_id, amount, date, description)
        )
        conn.commit()

    
    cursor.execute(
        "SELECT * FROM income WHERE user_id=%s ORDER BY income_date DESC",
        (user_id,)
    )
    income_data = cursor.fetchall()

    cursor.execute("""
        SELECT 
            DATE_FORMAT(i.income_date, '%%Y-%%m') AS month,
            SUM(i.amount) AS total_income,
            IFNULL(s.savings_amount, 0) AS savings
        FROM income i
        LEFT JOIN savings s
            ON s.user_id = i.user_id
            AND s.month_year = DATE_FORMAT(i.income_date, '%%Y-%%m')
        WHERE i.user_id=%s
        GROUP BY month
        ORDER BY month DESC
    """, (user_id,))

    monthly_income = cursor.fetchall()


    latest_month = monthly_income[0][0] if monthly_income else None
    latest_month_total = monthly_income[0][1] if monthly_income else 0


    savings_amount = 0
    if latest_month:
        cursor.execute(
            "SELECT savings_amount FROM savings WHERE user_id=%s AND month_year=%s",
            (user_id, latest_month)
        )
        s = cursor.fetchone()
        if s:
            savings_amount = s[0]

    cursor.close()
    conn.close()

    return render_template(
        'income.html',
        income=income_data,
        monthly_income=monthly_income,
        latest_month=latest_month,
        latest_total=latest_month_total,
        savings_amount=savings_amount
    )


@app.route('/edit_income/<int:id>', methods=['GET', 'POST'])
def edit_income(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        amount = request.form['amount']
        date = request.form['date']
        description = request.form['description']

        cursor.execute(
            "UPDATE income SET amount=%s, income_date=%s, description=%s WHERE income_id=%s",
            (amount, date, description, id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('income'))

    cursor.execute("SELECT * FROM income WHERE income_id=%s", (id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('edit_income.html', data=data)


@app.route('/delete_income/<int:id>')
def delete_income(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM income WHERE income_id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('income'))

@app.route('/save_savings', methods=['POST'])
def save_savings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    month = request.form['month']
    amount = request.form['savings']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM savings WHERE user_id=%s AND month_year=%s",
        (user_id, month)
    )

    if cursor.fetchone():
        cursor.execute(
            "UPDATE savings SET savings_amount=%s WHERE user_id=%s AND month_year=%s",
            (amount, user_id, month)
        )
    else:
        cursor.execute(
            "INSERT INTO savings (user_id, month_year, savings_amount) VALUES (%s, %s, %s)",
            (user_id, month, amount)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('income'))




@app.route('/expense', methods=['GET', 'POST'])

@app.route('/expense', methods=['GET', 'POST'])
def expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        amount = float(request.form['amount'])
        date = request.form['date']
        category = request.form['category']
        description = request.form['description']

        month = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m")

        cursor.execute("""
            SELECT IFNULL(SUM(amount),0)
            FROM income
            WHERE user_id=%s
            AND DATE_FORMAT(income_date, '%%Y-%%m')=%s
        """, (user_id, month))
        monthly_income = float(cursor.fetchone()[0])

        cursor.execute("""
            SELECT IFNULL(SUM(amount),0)
            FROM expense
            WHERE user_id=%s
            AND DATE_FORMAT(expense_date, '%%Y-%%m')=%s
        """, (user_id, month))
        monthly_expense = float(cursor.fetchone()[0])
        
        if monthly_expense + amount > monthly_income:
            flash("Expense exceeds total income for this month!", "danger")
        else:
            cursor.execute("""
                INSERT INTO expense (user_id, category, amount, expense_date, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, category, amount, date, description))
            conn.commit()
            flash("Expense added successfully!", "success")



    cursor.execute(
        "SELECT * FROM expense WHERE user_id=%s ORDER BY expense_date DESC",
        (user_id,)
    )
    expenses = cursor.fetchall()
    
    cursor.execute("""
    SELECT 
        DATE_FORMAT(expense_date, '%%Y-%%m') AS month,
        SUM(amount) AS total_expense
    FROM expense
    WHERE user_id=%s
    GROUP BY month
    ORDER BY month DESC
    """, (user_id,))

    monthly_expense = cursor.fetchall()


    cursor.close()
    conn.close()
    
    

    return render_template(
    'expance.html',
    expenses=expenses,
    monthly_expense=monthly_expense
)


@app.route('/edit_expense/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        amount = request.form['amount']
        date = request.form['date']
        category = request.form['category']
        description = request.form['description']

        cursor.execute(
            "UPDATE expense SET amount=%s, expense_date=%s, category=%s, description=%s "
            "WHERE expense_id=%s",
            (amount, date, category, description, id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('expense'))

    cursor.execute("SELECT * FROM expense WHERE expense_id=%s", (id,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('edit_expense.html', data=data)

@app.route('/delete_expense/<int:id>')
def delete_expense(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expense WHERE expense_id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('expense'))


@app.route('/expense_evaluation')
def expense_evaluation():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    selected_month = request.args.get('month') 

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT DATE_FORMAT(expense_date,'%%Y-%%m')
        FROM expense
        WHERE user_id=%s
        ORDER BY 1 DESC
    """, (user_id,))
    months = [row[0] for row in cursor.fetchall()]

    if not selected_month and months:
        selected_month = months[0] 

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM income
        WHERE user_id=%s
        AND DATE_FORMAT(income_date,'%%Y-%%m')=%s
    """, (user_id, selected_month))
    total_income = float(cursor.fetchone()[0])

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expense
        WHERE user_id=%s
        AND DATE_FORMAT(expense_date,'%%Y-%%m')=%s
    """, (user_id, selected_month))
    total_expense = float(cursor.fetchone()[0])

    balance = total_income - total_expense

    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expense
        WHERE user_id=%s
        AND DATE_FORMAT(expense_date,'%%Y-%%m')=%s
        GROUP BY category
    """, (user_id, selected_month))
    category_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "expense_evaluation.html",
        months=months,
        selected_month=selected_month,
        total_expense=total_expense,
        balance=balance,
        category_data=category_data
    )

@app.route('/budget')
def budget():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    current_month = datetime.now().strftime("%Y-%m")

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM income
        WHERE user_id=%s AND DATE_FORMAT(income_date,'%%Y-%%m')=%s
    """, (user_id, current_month))
    income = float(cursor.fetchone()[0])

    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expense
        WHERE user_id=%s AND DATE_FORMAT(expense_date,'%%Y-%%m')=%s
    """, (user_id, current_month))
    expense = float(cursor.fetchone()[0])

    cursor.execute("""
        SELECT IFNULL(savings_amount,0)
        FROM savings
        WHERE user_id=%s AND month_year=%s
    """, (user_id, current_month))
    savings = float(cursor.fetchone()[0] or 0)

    conn.close()

    available = income - savings

    if income == 0:
        alert_type = "info"
        message = "No income recorded for this month."
    elif expense < available * 0.7:
        alert_type = "success"
        message = "You are managing expenses well. Savings are safe."
    elif expense < available:
        alert_type = "warning"
        message = "You are close to using your savings. Control expenses."
    else:
        alert_type = "danger"
        message = "You are not able to save money this month."

    return render_template(
        'budget.html',
        income=income,
        expense=expense,
        savings=savings,
        available=available,
        alert_type=alert_type,
        message=message,
        month=current_month
    )




if __name__ == '__main__':
    app.run(debug=True)
