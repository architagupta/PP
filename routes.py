from models import db, User, PremiumCustomer
from forms import SignupForm, LoginForm, ForgotPassword
from flask import Flask, url_for, render_template, request, redirect, session, send_from_directory, send_file, jsonify
import smtplib
import string
from random import *
from werkzeug import generate_password_hash
from sendEmail import sendEmail
from utils import *
from flask_bootstrap import Bootstrap
from PIL import Image
from werkzeug.utils import secure_filename
import os
from flask_mail import Mail, Message
import paypalrestsdk
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import io

app = Flask(__name__)
filename = "NULL"
current_name = "NULL"
isPremium= False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:shreya@localhost/postgres'
db.init_app(app)
app.secret_key = "development-key"
app.config.from_pyfile('config.cfg')
mail = Mail(app)
s = URLSafeTimedSerializer('Thisisasecret!')

paypalrestsdk.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": "AQj6d--m2WHNfXp0H1KZp-Uw9QsaWlxdO3ZS7YUl7dRwJQZzaleQJOhcRqSvdiyo4V0aXhpjNTGZ3OxV",
  "client_secret": "EFSj_1IAKBwzd1_le4V8X2GPYv3RrDxvK0K-BIby8LxPaAddueAE4RU0fGzt6Bj2o5_9dIrmp_j5Efmz" })

Bootstrap(app)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
images_directory = os.path.join(APP_ROOT, 'imagesfolder')
thumbnails_directory = os.path.join(APP_ROOT, 'thumbnails')
@app.route("/")
def index():
    return render_template("/index.html")

@app.route("/nearest")
def nearesr_store():
  return render_template("/nearest_stores.html")

@app.route("/about")
def about():
  return render_template("/about.html")

@app.route('/signup.html', methods=["GET"])
def signupPage():
  form = SignupForm()
  return render_template('/signup.html',form=form)

@app.route('/signup/', methods=["POST"])
def signup():
  form = SignupForm()
  logform = LoginForm()
  if request.method == "POST":
    if form.validate() == False:
      return render_template('/signup.html', form=form)
    else:
      newuser = User(form.user_name.data, form.first_name.data, form.last_name.data, form.email.data, form.password.data)
      db.session.add(newuser)
      db.session.commit()
      # premuser = PremiumCustomer(form.user_name.data)
      # db.session.add(premuser)
      # db.session.commit()
      email = form.email.data
      token = s.dumps(email, salt='email-confirm')
      msg = Message('Confirm Email', sender='perfectpicture905@gmail.com', recipients=[email])
      link = url_for('confirm_email', token=token, _external=True)
      message= 'Your Registration link is {}'.format(link)
      msg.body=messageBody(message=message)
      mail.send(msg)
      return redirect(url_for('loginPage'))
    return render_template('/signup.html')

@app.route('/confirm_email/<token>')
def confirm_email(token):
    logform = LoginForm()
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        return render_template('/error.html',message="The token is expired!")
    user = User.query.filter_by(email = email).first()
    if user.confirmed:
        return render_template('/error.html',message="Account already confirmed. Please login.")
    else:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return render_template('/error.html',message="You have confirmed your account. Thanks!")
    return render_template('/login.html',form=logform)

@app.route('/login.html')
def loginPage():
    form = LoginForm()
    return render_template('/login.html',form=form)

@app.route('/login/', methods = ['GET', 'POST'])
def login():
  form = LoginForm()
  print(request.method)
  if request.method == "POST":
    if form.validate() == False:
      print(form.validate())
      return render_template("login.html", form = form)
    else :
      user_name = form.user_name.data
      password = form.password.data
      user = User.query.filter_by(username = user_name).first()
      if  user.confirmed == False:
          return render_template('/error.html',message="Please confirm your email id")
      session['username'] = form.user_name.data
      print(form.user_name.data)
      session['logged_in']=True
      return redirect(url_for('index'))
  else:
    return render_template('/login.html',form=form)
  return render_template('/error.html',message="Opps...Login Error. Please try again!")

@app.route("/logout.html")
def logout():
  session.pop('username', None)
  session['logged_in']=False
  return redirect(url_for('index'))

@app.route("/forgotpassword/",methods=["POST"])
def forgotpassword():
  form=ForgotPassword()
  user_name = form.user_name.data
  user = User.query.filter_by(username = user_name).first()
  if user is not None:
    allchar = string.ascii_letters + string.digits
    newpassword = "".join(choice(allchar) for x in range(randint(6,12)))
    msg = "your new password is" + newpassword
    print(msg)
    print(user.email)
    hashedpass=generate_password_hash(newpassword)
    admin = User.query.filter_by(username=user_name).update(dict(password=hashedpass))
    db.session.commit()
    message="Your new Password is " + newpassword
    msg=messageBody(message=message)
    if sendEmail(user.email,"Password Reset",msg):
      return render_template('/error.html',message="Email sent to "+user.email)
    else:
      return render_template('/error.html',message="Error when email sent to "+user.email)
  else:
     return render_template('/error.html',message="User does not Exsist")

@app.route('/linkage')
def link():
    return render_template('link.html')

@app.route('/gallery')
def gallery():
    if session.get('logged_in') == True:
        thumbnail_names = os.listdir('./thumbnails')
        return render_template('gallery.html', thumbnail_names=thumbnail_names)
    else:
        form = LoginForm()
        return render_template('/login.html',form=form)

@app.route('/thumbnails/<filename>')
def thumbnails(filename):
    return send_from_directory('thumbnails', filename)

@app.route('/imagesfolder/<filename>')
def images(filename):
    return send_from_directory('imagesfolder', filename)

@app.route('/public/<path:filename>')
def static_files(filename):
    return send_from_directory('./public', filename)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global filename
    if session.get('logged_in') == True:
        if request.method == 'POST':
            for upload in request.files.getlist('images'):
                current_uname= session['username']
                filename = current_uname + "_" + upload.filename
                filename = secure_filename(filename)
                # This is to verify files are supported
                ext = os.path.splitext(filename)[1][1:].strip().lower()
                if ext in set(['jpg', 'jpeg', 'png']):
                    print('File supported moving on...')
                else:
                    return render_template('error.html', message='Uploaded files are not supported...')
                destination = '/'.join([images_directory, filename])
                # Save original image
                upload.save(destination)
        return render_template('upload.html',image_name=filename)
    else:
        form = LoginForm()
        return render_template('/login.html',form=form)

@app.route('/findImge', methods=['GET', 'POST'])
def findImge():
    return filename

@app.route('/filteredImge', methods=['GET', 'POST'])
def filteredImge():
    return current_name

@app.route('/forgotpassword.html', methods=["GET"])
def forgotpasswordpage():
  form = ForgotPassword()
  return render_template('/forgotpassword.html',form=form)

@app.route('/gray/<filename>', methods=['GET', 'POST'])
def grayfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_gray=gray(destination=destination)
    hexdata,size= hex_convert(image_gray)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    return redirect(url_for('upload'))

@app.route('/rgb/<filename>', methods=['GET', 'POST'])
def rgbfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_rgb=rgb(destination=destination)
    hexdata,size= hex_convert(image_rgb)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    return redirect(url_for('upload'))

@app.route('/flip/<filename>', methods=['GET', 'POST'])
def flipfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_flip=flip(destination=destination)
    hexdata,size= hex_convert(image_flip)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_flip.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/galaxy/<filename>', methods=['GET', 'POST'])
def galaxyfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_galaxy=galaxy(destination=destination)
    hexdata,size= hex_convert(image_galaxy)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_galaxy.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/watercolor/<filename>', methods=['GET', 'POST'])
def watercolorfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_water=watercolor(destination=destination)
    hexdata,size= hex_convert(image_water)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_galaxy.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/blur/<filename>', methods=['GET', 'POST'])
def blurfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_blur=blur(destination=destination)
    hexdata,size= hex_convert(image_blur)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    return redirect(url_for('upload'))

@app.route('/sharp/<filename>', methods=['GET', 'POST'])
def sharpfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_sharp=sharp(destination=destination)
    hexdata,size= hex_convert(image_sharp)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)

    return redirect(url_for('upload'))

@app.route('/emboss/<filename>', methods=['GET', 'POST'])
def embossfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_emboss=blur(destination=destination)
    hexdata,size= hex_convert(image_emboss)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    return redirect(url_for('upload'))

@app.route('/edge/<filename>', methods=['GET', 'POST'])
def edgefilter(filename):
    destination = '/'.join([images_directory, filename])
    image_edge=edge(destination=destination)
    hexdata,size= hex_convert(image_edge)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    return redirect(url_for('upload'))

@app.route('/rotate/<filename>', methods=['GET', 'POST'])
def rotatefilter(filename):
    destination = '/'.join([images_directory, filename])
    image_rotate =rotate(destination=destination)
    hexdata,size= hex_convert(image_rotate)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_sharp.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/posterize/<filename>', methods=['GET', 'POST'])
def posterizefilter(filename):
    destination = '/'.join([images_directory, filename])
    image_posterize =posterize(destination=destination)
    hexdata,size= hex_convert(image_posterize)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_sharp.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/solarize/<filename>', methods=['GET', 'POST'])
def solarizefilter(filename):
    destination = '/'.join([images_directory, filename])
    image_solarize =solarize(destination=destination)
    hexdata,size= hex_convert(image_solarize)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    return redirect(url_for('upload'))

@app.route('/invert/<filename>', methods=['GET', 'POST'])
def invertfilter(filename):
    destination = '/'.join([images_directory, filename])
    image_invert =invert(destination=destination)
    hexdata,size= hex_convert(image_invert)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_sharp.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/redeye/<filename>', methods=['GET', 'POST'])
def redeyefilter(filename):
    destination = '/'.join([images_directory, filename])
    image_red =redEyeCorrect(destination=destination)
    hexdata,size= hex_convert(image_red)
    u_name= session.get('username')
    write_db(u_name,hexdata,size)
    # image_sharp.save('/'.join([thumbnails_directory, filename]))
    return redirect(url_for('upload'))

@app.route('/filtered', methods=['GET', 'POST'])
def filtered():
    global current_name
    current_user = session.get('username')
    current_name = read_db(current_user)
    return render_template('upload.html',filtered_image = current_name)

@app.route('/save/<save_file>', methods=['GET', 'POST'])
def save(save_file):
    destination = '/'.join([thumbnails_directory, save_file])
    print(destination)
    return send_file(destination,as_attachment=True,attachment_filename='Your Image.jpg',mimetype='image/jpeg')

@app.route('/discard/<image_name>', methods=['GET', 'POST'])
def discard(image_name):
    user = session.get('username')
    discard_image(user)
    file = '/'.join([thumbnails_directory,image_name])
    print(file)
    if os.path.isfile(file):
        os.unlink(file)
    else:
        print("Error: %s file not found" % file)
    return  redirect(url_for('gallery'))
@app.route('/pay')
def pay():
    return render_template('pay.html')

@app.route('/payment', methods=['POST'])
def payment():
    user= session['username']
    premuser = PremiumCustomer(user)
    db.session.add(premuser)
    db.session.commit()
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:5000/payment/execute",
            "cancel_url": "http://localhost:5000/"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "testitem",
                    "sku": "12345",
                    "price": "10.00",
                    "currency": "AUD",
                    "quantity": 1}]},
            "amount": {
                "total": "10.00",
                "currency": "AUD"},
            "description": "This is the payment transaction description."}]})

    if payment.create():
        print('Payment success!')
    else:
        return render_template('/error.html',message=payment.error)
        #print(payment.error)
    updateuser = PremiumCustomer.query.filter_by(username=user).first()
    updateuser.paymentid = payment.id
    db.session.commit()
    return jsonify({'paymentID' : payment.id})

@app.route('/execute', methods=['POST'])
def execute():
    success = False
    payment = paypalrestsdk.Payment.find(request.form['paymentID'])
    paymentid=request.form['paymentID']
    if payment.execute({'payer_id' : request.form['payerID']}):
        print('Execute success!')
        success = True
        updateuser = PremiumCustomer.query.filter_by(paymentid=paymentid).first()
        updateuser.paymentstatus = "Success"
        updateuser.ispremium = True
        db.session.commit()
    else:
        return render_template('/error.html',message=payment.error)
        #print(payment.error)

    return jsonify({'success' : success})

@app.route('/isPremium', methods=['GET','POST'])
def isPremium():
    u_name= session.get('username')
    a,b="0","1"
    updateuser = PremiumCustomer.query.filter_by(username=u_name).first()
    if updateuser.ispremium:
        return a
    else:
        return b

def messageBody(message):
    message_body = \
        """
        Dear User, \n
        %s
        \n Kind Regards, \n PicturePerfect Team."""%(message)
    return message_body

if __name__ == "__main__":
  app.run(debug=True)