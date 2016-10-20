# -*- coding: utf-8 -*-
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, url_for, redirect, \
	 render_template, abort, g, flash, _app_ctx_stack, jsonify, app
from werkzeug import check_password_hash, generate_password_hash
import urllib2, urllib ,json, ast, sys
from datetime import timedelta

reload(sys)
sys.setdefaultencoding('utf-8')

# configuration
DATABASE = './tmp/watermelon.db'
DEBUG = True
SECRET_KEY = 'development key'
APP_Key = 'your-key'

app = Flask(__name__)
app.config.from_object(__name__)

def get_db():
	top = _app_ctx_stack.top
	if not hasattr(top, 'sqlite_db'):
		top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
		top.sqlite_db.row_factory = sqlite3.Row
	return top.sqlite_db

@app.teardown_appcontext
def close_database(exception):
	top = _app_ctx_stack.top
	if hasattr(top, 'sqlite_db'):
		top.sqlite_db.close()

def init_db():
	with app.app_context():
		db = get_db()
		with app.open_resource('schema.sql', mode='r') as f:
			db.cursor().executescript(f.read())
		db.commit()

def query_db(query, args=(), one=False):
	cur = get_db().execute(query, args)
	rv = cur.fetchall()
	return (rv[0] if rv else None) if one else rv

def get_user_id(username):
	rv = query_db('select user_id from user where username = ?',
				  [username], one=True)
	return rv[0] if rv else None

def get_chart():
	db=get_db()
	db.execute('''delete  from chart''')
	ranking=""
	count=1
	page=0
	db=get_db()
	url="http://apis.skplanetx.com/melon/charts/realtime?version=1&page=0&count=100&format=json&appKey="+APP_Key
	res=urllib2.urlopen(url)
	data=json.load(res)
	for idx in data['melon']['songs']['song']:
		ranking=str(count)
		if count%20-1==0:
			page+=1
		db.execute('''insert into chart(ranking,songName,artists,page) values(?,?,?,?)''',[ranking.decode('utf-8'),idx['songName'],idx['artists']['artist'][0]['artistName'],page])
		count+=1
	db.commit()
	return "get_chart"

def get_musicID(name,singer):
	query=name+" "+singer+" audio"
	para=urllib.urlencode({"q":query})
	url="https://www.googleapis.com/youtube/v3/search?part=snippet&"+para+"&type=video&maxResults=1&key=AIzaSyC16ZCtNfJa-yKpGtgg9jX3u2psc9wDc2c"
	res=urllib2.urlopen(url)
	ex=json.load(res)
	idd=ex['items'][0]['id']['videoId']

	return idd

def get_music(query):
	para=urllib.urlencode({"searchKeyword":query})
	url="http://apis.skplanetx.com/melon/songs?count=10&page=1&"+para+"&version=1&format=json&appKey=6f7baadf-8d46-3a60-969d-62dc4e49e136"
	res=urllib2.urlopen(url)
	data=json.load(res)
	try: 
		data['melon']['songs']
		search_music=""
		for idx in data['melon']['songs']['song']:
				search_music += '<li class="collection-item avatar"><i class="mdi-av-my-library-music circle red"></i><span class="title">' + idx['songName'] + "</span>"
				search_music += "<p>" + idx['artists']['artist'][0]['artistName'] + "</p>"
				search_music += '<a href="' + url_for('add_music', songName = idx['songName'], singer = idx['artists']['artist'][0]['artistName'])
				search_music += '" class="secondary-content"><i class="mdi-content-add"></i></a></li>'
		return search_music
	except :
		return "목록이 없습니다."

def get_url(arr):
	download_url = ""
	url = "http://YoutubeInMP3.com/fetch/?api=advanced&format=JSON&video=http://www.youtube.com/watch?v="
	idd = arr.split(',')
	idd.pop()
	print idd
	js = None
	for i in idd:
		while True:
			try :
				res = urllib2.urlopen(url+i)
				js = json.load(res)
			except :
				"nothing"
			if js is not None:
				break;
		download_url += js['link']+","
		print js['link']
		js = None
	print download_url
	return jsonify(url = download_url)

@app.before_request
def make_session_parameter():
	session.permanet = True
	app.permanet_session_lifetime = timedelta(minutes=1)
	g.user = None
	if 'user_id' in session:
		g.user = query_db('select * from user where user_id = ?',
						  [session['user_id']], one=True)

@app.route('/')
def show_main():
	 if g.user:
	 	return redirect(url_for('public_main'))
	 else:
	 	return render_template('login.html') 
@app.route('/login/', methods=['GET', 'POST'])
def login():
	if g.user:
		return redirect(url_for('public_main'))
	error = None
	if request.method == 'POST':
		user = query_db('''select * from user where username = ?''', [request.form['username']], one=True)
		if user is None:
			error = '아이디가 올바르지 않습니다'
		elif not check_password_hash(user['pw_hash'],
									 request.form['password']):
			error = '비밀번호가 올바르지 않습니다.'
		else:
			flash('You were logged in')
			session['user_id'] = user['user_id']
			return redirect(url_for('public_main'))
	return render_template('login.html', error=error)


@app.route('/register/', methods=['GET', 'POST'])
def register():
	if g.user:
		return redirect(url_for('show_main'))
	error = None
	if request.method == 'POST':
		if not request.form['username']:
			error = '아이디를 입력하세요'
		elif not request.form['email'] or \
				 '@' not in request.form['email']:
			error = '올바른 이메일 주소를 입력하세요'
		elif not request.form['password']:
			error = '비밀번호를 입력하세요'
		elif request.form['password'] != request.form['password2']:
			error = '두 비밀번호가 일치하지 않습니다'
		elif get_user_id(request.form['username']) is not None:
			error = '이미 존재하는 아이디입니다'
		else:
			db = get_db()
			db.execute('''insert into user (
			  username, email, pw_hash) values (?, ?, ?)''',
			 [request.form['username'], request.form['email'],
			   generate_password_hash(request.form['password'])])
			db.commit()
			flash('You were successfully registered and can login now')
			return redirect(url_for('login'))
	return render_template('register.html', error=error)

@app.route('/logout/')
def logout():
	flash('You were logged out')
	session.pop('user_id', None)
	return redirect(url_for('show_main'))

@app.route('/public/' , methods=['GET','POST'])
def public_main():
	if g.user:
		if request.method == 'POST':
			return redirect(url_for('search',songName=request.form['search']))
		db=get_db()
		page=1
		chart=query_db('''select ranking,songName,artists from chart where page=1''')
		return render_template('public_index.html',data=chart,page=page)
	else:
		return redirect(url_for('show_main'))


@app.route('/public/add/<string:songName>')
def add_music(songName):
	if g.user:
		db=get_db()
		name="".join(songName).strip()
		singer=request.args.get('singer')
		if singer is None:
			singer= query_db('''select artists from chart where songName=?''',[songName],one=True)
			music_id=get_musicID(name,singer[0])
		else:
			music_id=get_musicID(name,singer)
		db.execute('''insert into music(user_id,like_music,music_id) values(?,?,?) ''',[session['user_id'],songName,music_id])
		db.commit()
		return redirect(url_for('public_main'))
	else:
		redirect(url_for('login'))

@app.route('/public/delete/<string:songName>')
def delete_music(songName):
	if g.user:
		db=get_db()
		db.execute('''delete from music where like_music=?''',[songName])
		db.commit()
		return redirect(url_for('play_list'))
	else:
		redirect(url_for('login'))

@app.route('/public/addChart')
def add_chart():
	data=query_db('''select ranking,songName,artists from chart''')
	songName=[]*20
	singer=[]*20
	rank=[]*20 
	for idx in data:
		rank.append(idx[0])
		songName.append(idx[1])
		singer.append(idx[2])
	return jsonify(rank=rank, songName=songName, singer=singer)

@app.route('/public/lessChart')
def less_chart():
	page=request.args.get('page', 0, type=int)
	page-=1
	if page!=0:
	   data=query_db('''select ranking,songName,artists from chart where page=?''',[page])
	   addmusic=""
	   for idx in data:
			addmusic += "<a href='" + url_for('add_music', songName=idx[1]) + "'> "
			addmusic += "<h6>"+idx[0]+" "+idx[1]+" "+idx[2]+"</h6>"
			addmusic += "</a>"
	else :
		addmusic="더이상 목록이 없습니다"
	return jsonify(page=page,result=addmusic)

@app.route('/public/playlist/')
def play_list():
	db=get_db()
	db_music = query_db('''select like_music from music where user_id=?''',[session['user_id']])
	music_id=query_db('''select music_id from music where user_id=?''',[session['user_id']])
	data=""
	for i in music_id:
		for order in i:
			data += order+","

	return render_template('playlist.html' ,playlist=db_music, music_id=data)

@app.route('/public/search/' , methods=['GET','POST'])
def search():
	search_data=None
	if request.method=='POST':
		search_data = get_music(request.form['search'])
		return render_template('search.html', data=search_data)

	return render_template('search.html')

@app.route('/chart')
def new():
	get_chart()
	return redirect(url_for('show_main'))

@app.route('/public/download')
def down_music():
	arr = request.args.get('id',type=str)
	return get_url(arr)

if __name__ == '__main__':
	app.run(host='0.0.0.0',debug=True)
