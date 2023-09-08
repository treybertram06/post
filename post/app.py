from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import os
from flask_migrate import Migrate


app = Flask(__name__)
app.config['SECRET_KEY'] = 'bc7e899d8a14097cabd7cca66d97c3c7'

login_manager = LoginManager()
login_manager.init_app(app)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    likes = db.relationship('Like', backref='user', lazy='dynamic')


    def __repr__(self):
        return '<User %r>' % self.username

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    image = db.Column(db.String(120), nullable=True)
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade="all, delete-orphan")

    def count_likes(self):
        return Like.query.filter_by(post_id=self.id, like=True).count()

    def count_dislikes(self):
        return Like.query.filter_by(post_id=self.id, dislike=True).count()
        
    def __repr__(self):
        return '<Post %r>' % self.title

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    like = db.Column(db.Boolean, nullable=False, default=False)
    dislike = db.Column(db.Boolean, nullable=False, default=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def __repr__(self):
        return '<Comment %r>' % self.content
    
    def count_likes(self):
        return CommentLike.query.filter_by(comment_id=self.id, like=True).count()

    def count_dislikes(self):
        return CommentLike.query.filter_by(comment_id=self.id, dislike=True).count()

class CommentLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    like = db.Column(db.Boolean, nullable=False, default=False)
    dislike = db.Column(db.Boolean, nullable=False, default=False)
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    posts = Post.query.all()
    return render_template('index.html', posts=posts)

@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory('uploads', filename)

@app.route('/registration')
def registrationPage():
    return render_template('registration.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return jsonify(success=True)
        else:
            return jsonify(success=False, message='Invalid username or password')
    else:
        return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/post', methods=['POST'])
@login_required
def post():
    title = request.form.get('title')
    content = request.form.get('content')
    post = Post(title=title, content=content, user=current_user)
    image = request.files.get('image')
    if image:
        filename = secure_filename(image.filename)
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        image.save(os.path.join('uploads', filename))
        post.image = filename
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/post/<id>', methods=['DELETE'])
@login_required
def delete_post(id):
    post = Post.query.get(id)
    if post and post.user == current_user:
        db.session.delete(post)
        db.session.commit()
    return '', 204  # return no content status

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    post = Post.query.get(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if like:
        like.like = True
        like.dislike = False
    else:
        like = Like(user_id=current_user.id, post_id=post_id, like=True)
        db.session.add(like)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/dislike/<int:post_id>', methods=['POST'])
@login_required
def dislike(post_id):
    post = Post.query.get(post_id)
    dislike = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if dislike:
        dislike.dislike = True
        dislike.like = False
    else:
        dislike = Like(user_id=current_user.id, post_id=post_id, dislike=True)
        db.session.add(dislike)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment(post_id):
    content = request.form.get('content')
    comment = Comment(content=content, user=current_user, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get(comment_id)
    if comment and comment.user == current_user:
        db.session.delete(comment)
        db.session.commit()
    return '', 204  # return no content status

@app.route('/comment/like/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.get(comment_id)
    like = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()
    if like:
        like.like = True
        like.dislike = False
    else:
        like = CommentLike(user_id=current_user.id, comment_id=comment_id, like=True)
        db.session.add(like)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/dislike/<int:comment_id>', methods=['POST'])
@login_required
def dislike_comment(comment_id):
    comment = Comment.query.get(comment_id)
    dislike = CommentLike.query.filter_by(user_id=current_user.id, comment_id=comment_id).first()
    if dislike:
        dislike.dislike = True
        dislike.like = False
    else:
        dislike = CommentLike(user_id=current_user.id, comment_id=comment_id, dislike=True)
        db.session.add(dislike)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:parent_id>/reply', methods=['POST'])
@login_required
def reply(parent_id):
    content = request.form.get('content')
    parent_comment = Comment.query.get(parent_id)
    reply = Comment(content=content, user=current_user, post_id=parent_comment.post_id, parent_id=parent_id)
    db.session.add(reply)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('query')
    posts = Post.query.filter(or_(Post.title.like('%' + query + '%'), User.username.like('%' + query + '%'))).join(User).all()
    return render_template('search.html', posts=posts, query=query)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=3000)