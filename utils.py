from flask import Flask, render_template, redirect, url_for, send_from_directory, request
from flask_bootstrap import Bootstrap
from PIL import Image, ImageEnhance,ImageChops,ImageFilter, ImageOps
from werkzeug.utils import secure_filename
import os
import shutil
import io
from datetime import datetime, timezone
import psycopg2
import numpy as np
import cv2

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
images_directory = os.path.join(APP_ROOT, 'imagesfolder')
thumbnails_directory = os.path.join(APP_ROOT, 'thumbnails')

if not os.path.isdir(images_directory):
    os.mkdir(images_directory)
if not os.path.isdir(thumbnails_directory):
    os.mkdir(thumbnails_directory)

def emptyDir(thumbnails):
    for the_file in os.listdir(thumbnails):
        file_path = os.path.join(thumbnails, the_file)
        if os.path.isfile(file_path):
            os.unlink(file_path)

def gray(destination):
    image = Image.open(destination)
    image_gray = image.convert('L')
    return image_gray

def rgb(destination):
    image = Image.open(destination)
    image_rgb = image.convert('RGB')
    return image_rgb

def flip(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_flip = image.transpose(Image.FLIP_LEFT_RIGHT)
    return image_flip

def galaxy(destination):
    #destination = '/'.join([images_directory, filename])
    galaxy_filter = Image.open('galaxy.jpg')
    image = Image.open(destination)
    image_galaxy = ImageChops.add(galaxy_filter,image,3,1)
    return image_galaxy

def watercolor(destination):
    #destination = '/'.join([images_directory, filename])
    water_filter = Image.open('watercolor.jpg')
    image = Image.open(destination)
    image_water = ImageChops.add(water_filter,image,3,1)
    return image_water

def blur(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_blur = image.filter(ImageFilter.BLUR)
    return image_blur

def sharp(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_sharp = image.filter(ImageFilter.SHARPEN)
    return image_sharp

def emboss(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_emboss = image.filter(ImageFilter.EMBOSS)
    return image_emboss

def edge(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_edge = image.filter(ImageFilter.FIND_EDGES)
    return image_edge

def posterize(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_posterize = (ImageOps.posterize(image,1))
    return image_posterize

def rotate(destination):
    #destination = '/'.join([images_directory, filename])
    image = Image.open(destination)
    image_rotate = image.rotate(18, expand=True)
    return image_rotate

def solarize(destination):
    image = Image.open(destination)
    image_solarize = (ImageOps.solarize(image,1))
    return image_solarize

def invert(destination):
    image = Image.open(destination)
    image_invert = (ImageOps.invert(image))
    return image_invert

def fillGaps(mask):
    maskFloodfill = mask.copy()
    h, w = maskFloodfill.shape[:2]
    maskTemp = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(maskFloodfill, maskTemp, (0, 0), 255)
    mask2 = cv2.bitwise_not(maskFloodfill)
    return mask2 | mask

def redEyeCorrect(destination):
    face_cascade = cv2.CascadeClassifier('C:\\Users\\Vibhuti\\Anaconda3\\Lib\\site-packages\\cv2\\data\\haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier('C:\\Users\\Vibhuti\\Anaconda3\\Lib\\site-packages\\cv2\\data\\haarcascade_eye.xml')
    img = cv2.imread(destination)
    outputImg = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    for (x,y,w,h) in faces:
        # cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
        roi_gray = gray[y:y + h, x:x + w]
        roi_color = img[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray)
        for (ex,ey,ew,eh) in eyes:
            print(eyes)
            eye = img[y:y + h, x:x + w]
            b = eye[:, :, 0]
            g = eye[:, :, 1]
            r = eye[:, :, 2]
            print("done bgr")
            # Add the green and blue channels.
            bg = cv2.add(b, g)
            # Simple red eye detector.
            mask = ((r > 140) & (r > (bg))).astype(np.uint8) * 255
            print("done mask")
            # Convert the mask to uint8 format.
            #mask = mask.astype(np.uint8)*255
            # Clean mask -- 1) File holes 2) Dilate (expand) mask.
            mask = fillGaps(mask)
            mask = cv2.dilate(mask, None, anchor=(-1, -1), iterations=3, borderType=1, borderValue=1)
            # Calculate the mean channel by averaging
            # the green and blue channels
            mean = bg / 2
            mask = mask.astype(np.bool)[:, :, np.newaxis]
            mean = mean[:, :, np.newaxis]
            print("done mean")
            # Copy the eye from the original image.
            eyeOrigin = eye.copy()
            # Copy the mean image to the output image.
            #np.copyto(eyeOut, mean, where=mask)
            eyeOrigin = np.where(mask, mean, eyeOrigin)
            # Copy the fixed eye to the output image.
            outputImg[y:y + h, x:x + w, :] = eyeOrigin
    image_red = Image.fromarray(outputImg)
    return image_red

def write_db(u_name,hexdata,size):
    conn = None
    try:
        # connect to the PostgresQL database
        conn = psycopg2.connect("dbname=postgres user=postgres")
        # create a new cursor object
        cur = conn.cursor()
        # execute the INSERT statemen
        utc_dt = datetime.now(timezone.utc) # UTC time
        dt = utc_dt.astimezone()
        cur.execute("INSERT INTO images(user_name,image_data,timestamp,image_size) " + "VALUES(%s,%s,%s,%s)",
                    (u_name,hexdata,dt,size))
        # commit the changes to the database
        conn.commit()
        # close the communication with the PostgresQL database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def read_db(user_name):
    """ read BLOB data from a table """
    conn = None
    conn = psycopg2.connect("dbname=postgres user=postgres")
    # create a new cursor object
    cursor = conn.cursor()
    # execute the SELECT statement
    cursor.execute("SELECT id, image_data, user_name FROM images WHERE user_name=%s ORDER  BY timestamp DESC LIMIT  1",(user_name,))
    #"SELECT id,image_data from images WHERE id =
    #nextval(pg_get_serial_sequence('images', 'id'))-1;"
    user_data = cursor.fetchone()
    image_id = user_data[0]
    data = user_data[1]
    u_name = user_data[2]
    current_name = u_name + str(image_id) + "." + 'jpg'
    path = os.path.join(thumbnails_directory,  u_name + str(image_id) + "." + 'jpg')
    image = open(path, 'wb').write(user_data[1])
    cursor.close()
    return current_name

def fetch_db(user_name):
    """ read BLOB data from a table """
    conn = None
    conn = psycopg2.connect("dbname=postgres user=postgres")
    # create a new cursor object
    cursor = conn.cursor()
    # execute the SELECT statement
    cursor.execute("SELECT id, image_data, user_name FROM images WHERE user_name=%s ORDER  BY timestamp ",(user_name,))
    #"SELECT id,image_data from images WHERE id =
    #nextval(pg_get_serial_sequence('images', 'id'))-1;"
    user_data = cursor.fetchone()
    while user_data is not None:
        for user in user_data:
            image_id = user_data[0]
            data = user_data[1]
            u_name = user_data[2]
            current_name = u_name + str(image_id) + "." + 'jpg'
            path = os.path.join(thumbnails_directory,  u_name + str(image_id) + "." + 'jpg')
            image = open(path, 'wb').write(user_data[1])
        user_data = cursor.fetchone()
    cursor.close()

def discard_image(user):
    conn = None
    conn = psycopg2.connect("dbname=postgres user=postgres")
    # create a new cursor object
    cursor = conn.cursor()
    # execute the SELECT statement
    cursor.execute("delete from images where id in (select id from images order by id desc limit 1) AND user_name= %s",(user,))
    conn.commit()
    cursor.close()
    conn.close()

def hex_convert(filter_type):
    output = io.BytesIO()
    filter_type.save(output, format='jpeg')
    hexdata = output.getvalue()
    size = len(hexdata)
    return hexdata,size