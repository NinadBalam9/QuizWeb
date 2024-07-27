from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizbuddy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Define Quiz model
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # duration in minutes
    questions = db.relationship('Question', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    options = db.relationship('Option', backref='question', lazy=True)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return "Email already registered!"

    new_user = User(email=email, phone=phone, password=password)
    db.session.add(new_user)
    db.session.commit()
    
    return redirect(url_for('home'))

# Add more routes here for creating and managing quizzes

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if request.method == 'POST':
        title = request.form['title']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        duration_str = request.form['duration']

        # Validation for date/time and duration
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            duration = int(duration_str)
        except ValueError:
            return "Invalid date/time format or duration. Please check your input."

        if start_time >= end_time:
            return "End time must be after start time."

        # Create and save the new quiz
        new_quiz = Quiz(title=title, start_time=start_time, end_time=end_time, duration=duration)
        db.session.add(new_quiz)
        db.session.commit()

        return f"Quiz created successfully! Access link: /take_quiz/{new_quiz.id}"

    return render_template('create_quiz.html')



@app.route('/take_quiz/<int:quiz_id>', methods=['GET'])
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    current_time = datetime.now()

    # Check if the current time is within the quiz availability window
    if current_time < quiz.start_time or current_time > quiz.end_time:
        return "Quiz is not available at this time."

    return render_template('take_quiz.html', quiz=quiz)


@app.route('/submit_answers/<int:quiz_id>', methods=['POST'])
def submit_answers(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if datetime.now() < quiz.start_time or datetime.now() > quiz.end_time:
        return "Quiz is not available at this time."

    answers = request.form
    results = []
    student_email = request.form.get('email')  # Get student email from the form

    for question_id, option_id in answers.items():
        if question_id.startswith('question_'):
            question_id = int(question_id.split('_')[1])
            selected_option = Option.query.get_or_404(int(option_id))
            question = Question.query.get_or_404(question_id)
            correct_option = Option.query.filter_by(question_id=question_id, is_correct=True).first()
            if selected_option.is_correct:
                results.append((question.text, True))
            else:
                results.append((question.text, False))

    # Prepare email content
    result_body = "\n".join([f"{question}: {'Correct' if is_correct else 'Incorrect'}" for question, is_correct in results])
    send_email('Your Quiz Results', student_email, result_body)

    # Notify teacher (example, assuming you have teacher's email)
    teacher_email = 'teacher@example.com'  # Replace with actual teacher's email
    teacher_body = "\n".join([f"{question}: {'Correct' if is_correct else 'Incorrect'}" for question, is_correct in results])
    send_email('Student Quiz Results', teacher_email, teacher_body)

    return render_template('results.html', results=results)


app.config['MAIL_SERVER'] = 'smtp.example.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587  # Typically 587 for TLS
app.config['MAIL_USERNAME'] = 'your-email@example.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-email-password'  # Replace with your email password
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# Function to send email
def send_email(subject, recipient, body):
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.body = body
    mail.send(msg)