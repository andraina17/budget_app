"""
Flask web application replicating a simple budget tracker similar to the user's Google Sheets budget.

This application provides a basic UI/UX built with Bootstrap and uses an SQLite database
to persist data. Users can create accounts, record transactions (debits and credits),
and view summaries of their financial activities. It demonstrates how to replace a
spreadsheet-driven workflow with a proper web application backed by a database.
"""

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = "change_this_secret_key"  # Needed for flash messages

# Set up SQLite database relative to this file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "budget.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Account(db.Model):
    """Represents a bank or budget account."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    transactions = db.relationship('Transaction', backref='account', lazy=True)


class Transaction(db.Model):
    """Represents a debit or credit transaction for an account."""
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'Debit' or 'Credit'


@app.before_first_request
def create_tables():
    """Create database tables if they do not exist."""
    db.create_all()


@app.route('/')
def index():
    """Home page with navigation options."""
    return render_template('index.html')


@app.route('/accounts')
def list_accounts():
    """List all accounts and their balances."""
    accounts = Account.query.all()
    return render_template('accounts.html', accounts=accounts)


@app.route('/accounts/add', methods=['GET', 'POST'])
def add_account():
    """Add a new account."""
    if request.method == 'POST':
        name = request.form.get('name')
        try:
            balance = float(request.form.get('balance') or 0.0)
        except ValueError:
            balance = 0.0
        if not name:
            flash('Account name is required.', 'danger')
        else:
            account = Account(name=name, balance=balance)
            db.session.add(account)
            db.session.commit()
            flash('Account added successfully.', 'success')
            return redirect(url_for('list_accounts'))
    return render_template('add_account.html')


@app.route('/transactions')
def list_transactions():
    """List all transactions with account names."""
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    accounts = {acc.id: acc.name for acc in Account.query.all()}
    return render_template('transactions.html', transactions=transactions, accounts=accounts)


@app.route('/transactions/add', methods=['GET', 'POST'])
def add_transaction():
    """Add a new transaction (debit or credit) for an account."""
    accounts = Account.query.all()
    if not accounts:
        flash('Please create an account first.', 'warning')
        return redirect(url_for('add_account'))
    if request.method == 'POST':
        try:
            account_id = int(request.form.get('account_id'))
        except (ValueError, TypeError):
            account_id = None
        date_str = request.form.get('date')
        description = request.form.get('description') or ''
        try:
            amount = float(request.form.get('amount'))
        except (ValueError, TypeError):
            amount = 0.0
        trans_type = request.form.get('type') or 'Debit'
        # Validate required fields
        if not (account_id and date_str and description and amount):
            flash('All fields are required and amount must be numeric.', 'danger')
        else:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            transaction = Transaction(account_id=account_id,
                                      date=date,
                                      description=description,
                                      amount=amount,
                                      type=trans_type)
            db.session.add(transaction)
            # Update account balance depending on transaction type
            account = Account.query.get(account_id)
            if trans_type.lower() == 'credit':
                account.balance += amount
            else:
                account.balance -= amount
            db.session.commit()
            flash('Transaction added successfully.', 'success')
            return redirect(url_for('list_transactions'))
    return render_template('add_transaction.html', accounts=accounts)


@app.route('/summary')
def summary():
    """Display summary statistics for accounts and transactions."""
    accounts = Account.query.all()
    summary_data = []
    for acc in accounts:
        total_debits = sum(t.amount for t in acc.transactions if t.type.lower() == 'debit')
        total_credits = sum(t.amount for t in acc.transactions if t.type.lower() == 'credit')
        summary_data.append({
            'account': acc,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'net_change': total_credits - total_debits
        })
    return render_template('summary.html', summary_data=summary_data)


if __name__ == '__main__':
    """
    When executed directly, run the development server. When deploying to a platform like Railway
    or Heroku, the port is provided via the PORT environment variable. Fallback to port 5000 for
    local development.
    """
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)