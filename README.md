# tw-bot

Twitter bot script.

## Preparation

### Libraries

```shell
$ sudo pip install python-dotenv requests-oauthlib
```

### .env

```shell
$ cp -p .env-example .env
$ vi .env
```

## Usage

```shell
usage: bot.py [-h] [--text TEXT] [--image-dir IMAGE_DIR] [--image IMAGE]

Twitter bot script

optional arguments:
  -h, --help            show this help message and exit
  --text TEXT           Text posted as a tweet.
  --image-dir IMAGE_DIR
                        Use image files randomly selected in this directory
  --image IMAGE         Use the specified image file and --image-dir will be ignored.

```

## Example

[@NinjaDevBot](https://twitter.com/NinjaDevBot): post images generated by StyleGAN and StyleGAN2.

```shell
$ python bot.py --text="Generated with #DeepLearning #MachineLearning #StyleGAN #AI" \
    --image-dir /path/to/images/
```
