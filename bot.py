#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from dotenv import load_dotenv
import os, sys, json, glob, textwrap, argparse, mimetypes, pprint, random, time

from requests_oauthlib import OAuth1Session

HR = "----------------------"

# arg parse
argparser = argparse.ArgumentParser(
	formatter_class=argparse.RawDescriptionHelpFormatter,
	description="Twitter bot script", 
	epilog=("%s\nsee more detail at https://github.com/kaz-yamam0t0/tw-bot" % HR),
)
argparser.add_argument("--text", help="Text posted as a tweet.", default="")
argparser.add_argument("--image-dir", help="Use image files randomly selected in this directory", default="assets/images/")
argparser.add_argument("--image", help="Use the specified image file and --image-dir will be ignored.", default="")
# argparser.add_argument("--forever", help="Make this script run forever", action="store_true")
# argparser.add_argument("--duration", help="Interval seconds between posts (minimum is 3600), used only when --forever is specified.", default=1, type=int)
args = argparser.parse_args()

# global vars
_sess = None # Twitter API Session

# utils 
def debug(v):
	if os.getenv("BOT_ENV") == "development":
		import pprint
		print(pprint.pformat(v))

def out(v):
	print(v)

def die(errmsg="", exit_code=-1):
	if errmsg:
		print("[Error] %s" % errmsg)
		print(HR)
	
	global argparser
	argparser.print_help()

	sys.exit(exit_code)

# API functions ====================
def api_get(url, params=None):
	global _sess

	if url[0] == '/':
		url = 'https://api.twitter.com' + url

	res = _sess.get(url, params=params)
	if res.status_code < 200 or 300 <= res.status_code:
		raise Exception("status_code: %d\nresponse: %s" % (int(res.status_code), res.text, ))

	return json.loads(res.text)

def api_post(url, data=None, jsondata=None, files=None, no_response=False):
	global _sess

	if url[0] == '/':
		url = 'https://api.twitter.com' + url

	res = _sess.post(url, json=jsondata, data=data, files=files)
	if res.status_code < 200 or 300 <= res.status_code:
		raise Exception("status_code: %d\nresponse: %s" % (int(res.status_code), res.text, ))

	if no_response:
		return

	return json.loads(res.text)

def api_upload(p):
	CHUNK_SIZE = 1 * 1024 * 1024

	if not os.path.isfile(p):
		raise Exception("%s is not a file" % p)

	# `mimetypes.guess_type` guesses the type of a file based on its filename.
	# it doesn't check the file content.
	(mime, encoding_) = mimetypes.guess_type(p)
	if not mime: raise Exception("unknown ext: %s" % p)
	if not mime.startswith("image/"): raise Exception("%s is not an image." % p)

	with open(p, 'rb') as fp:
		total = os.path.getsize(p)

		# init
		data = api_post("https://upload.twitter.com/1.1/media/upload.json", data={
			"command" : "INIT" , 
			"total_bytes" : total, 
			"media_type" : mime, 
		})
		media_id = data.get("media_id_string")
		if not media_id:
			raise Exception("media_id is empty. : %s" % data)

		# append
		idx = 0
		pos = 0
		while pos < total:
			api_post("https://upload.twitter.com/1.1/media/upload.json", data={
				"command" : "APPEND" , 
				"media_id" : media_id , 
				"segment_index" : idx, 
			}, files={
				"media" : fp.read(CHUNK_SIZE)
			}, no_response=True)

			idx += 1
			pos = fp.tell()
			if idx > int(total / CHUNK_SIZE) + 1 or (pos < total and pos < CHUNK_SIZE * idx * 0.8):
				raise Exception("something seems wrong.")
			
		# finalize
		data = api_post("https://upload.twitter.com/1.1/media/upload.json", data={
			"command" : "FINALIZE" , 
			"media_id" : media_id , 
		})
		if media_id != data.get("media_id_string"):
			raise Exception("media_id is invalid : %s" % data)

		return media_id


# main ====================
if __name__ == '__main__':
	# find image
	if not args.image and not args.image_dir:
		die("Either --image or --image-dir is required.")

	images = None
	image = args.image
	image_dir = args.image_dir
	
	if image:
		image = os.path.abspath(image)
		if not os.path.isfile(image):
			die("%s is not a file" % image)
		images = [image, ]
	elif image_dir:
		image_dir = os.path.abspath(image_dir)
		if not os.path.isdir(image_dir):
			die("%s is not a directory" % image_dir)

		images = [p for p in glob.glob(image_dir+"/**", recursive=True) \
						if os.path.isfile(p) and (
							p[-4:] == ".png" or 
							p[-5:] == ".jpeg" or 
							p[-4:] == ".jpg" or 
							p[-4:] == ".gif"
						)  ]

	if len(images) <= 0:
		die("no image found")

	# load .env
	load_dotenv()
	if not os.getenv("CONSUMER_KEY"): die("`CONSUMER_KEY` is empty.", -1)
	if not os.getenv("CONSUMER_SECRET"): die("`CONSUMER_SECRET` is empty.", -1)
	if not os.getenv("ACCESS_TOKEN"): die("`ACCESS_TOKEN` is empty.", -1)
	if not os.getenv("ACCESS_TOKEN_SECRET"): die("`ACCESS_TOKEN_SECRET` is empty.", -1)

	# create session
	_sess = OAuth1Session(
		os.getenv("CONSUMER_KEY"), 
		os.getenv("CONSUMER_SECRET"), 
		os.getenv("ACCESS_TOKEN"),
		os.getenv("ACCESS_TOKEN_SECRET")
	)

	# debug(args)

	# get my own id
	# not necessary if what you want to do is just to post tweets
	"""
	me = api_get("/2/users/me")
	if not me or not me.get("data") or not me.get("data").get("id"):
		raise Exception("failed to get my own data")

	me = me.get("data")
	my_id = me.get("id")

	out("my id: %s" % my_id)
	"""

	def upload():
		global images, args

		f = images[ random.randrange(len(images)) ]
		media_id = api_upload(f)
		# debug(media_id)

		# tweets
		# Reference: https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
		res = api_post("/2/tweets", jsondata={ 
			"text" : args.text,
			"media" : {
				"media_ids" : [ media_id, ] ,
			},
		})
		out(pprint.pformat(res))

	# use crontab instead of --forever
	# 
	# if args.forever:
	# 	d = max(3600, args.duration)
	# 	while True:
	# 		upload()
	# 		time.sleep(d)
	# else:
	# 	upload()
	upload()

	# time.sleep(60 * 10)
