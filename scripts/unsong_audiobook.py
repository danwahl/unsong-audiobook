from datetime import datetime
from io import BytesIO
import os
import pytz
import re
import sys
import urllib
import urllib3

from bs4 import BeautifulSoup
from pydub import AudioSegment
import boto3
import nltk.data

# silence timing, in ms
PARAGRAPH_SILENCE = 557
SENTENCE_SILENCE = 316

# relative directory paths
CHAPTERS_PATH = '../chapters/'
POSTS_PATH = '../_posts/'

# link to unsong contents
UNSONG_CONTENTS = 'https://unsongbook.com/'


def get_audio(text):
    response = polly_client.synthesize_speech(
        VoiceId='Matthew', Engine='neural', OutputFormat='mp3', Text=text)
    seg = BytesIO()
    seg.write(response['AudioStream'].read())
    seg.seek(0)
    return seg


if __name__ == '__main__':
    num = 0

    # setup nltk tokenizer
    # uncomment following line on first run
    # nltk.download('punkt')
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

    # setup polly client
    # todo(dan): move keys to separate file
    polly_client = boto3.Session(
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        region_name='us-west-2').client('polly')

    # setup urllib pool manager
    http = urllib3.PoolManager()

    # get and parse contents
    res = http.request('GET', UNSONG_CONTENTS)
    soup = BeautifulSoup(res.data, "html.parser")

    # get divs containing post links, iterate through list in reverse order
    contents = soup.find('div', attrs={'class': 'pjgm-postcontent'})
    anchors = contents.find_all('a', href=True)
    for anchor in anchors:
        # get post url
        url = anchor['href']

        # get post name and build chapter filename
        name = urllib.parse.unquote(url.split('/')[-2])
        filename = name + '.mp3'

        # check if filename already exists in chapters folder, skip if so
        if filename in os.listdir(CHAPTERS_PATH):
            continue

        # get post and parse
        res = http.request('GET', url)
        soup = BeautifulSoup(res.data, "html.parser")

        # get post content, get author, title, date, and time
        post = soup.find('div', attrs={'id': re.compile(r'post\-\d+')})
        author = post.find('a', attrs={'class': 'url fn n'}).text
        title = post.find('h1', attrs={'class': 'pjgm-posttitle'}).text
        date = post.find('span', attrs={'class': 'entry-date'}).text
        time = post.find(
            'div', attrs={
                'class': 'pjgm-postmeta'}).find('a').get('title')

        # create timezone aware datetime object from date and time
        dt = datetime.strptime(' '.join([date, time]), '%B %d, %Y %I:%M %p')
        dtz = pytz.timezone("US/Pacific").localize(dt)

        print(dtz.strftime('%Y-%m-%d ') + name)

        # initialize pydub object
        chapter = AudioSegment.silent(PARAGRAPH_SILENCE)

        # split post into paragraphs, iterate through list
        paragraphs = post.find_all('p')
        for paragraph in paragraphs:
            # split paragraph by new lines, iterate through list
            for line in paragraph.text.split('\n'):
                # split line into sentences, iterate through each
                sentences = tokenizer.tokenize(line)
                for sentence in sentences:
                    # add sentence audio and silence to chapter
                    chapter += AudioSegment.from_mp3(get_audio(sentence))
                    chapter += AudioSegment.silent(duration=SENTENCE_SILENCE)
                # add slightly longer pause between paragraphs
                chapter += AudioSegment.silent(PARAGRAPH_SILENCE -
                                               SENTENCE_SILENCE)

        # export chapter, get file duration and length
        chapter.export(
            CHAPTERS_PATH +
            filename,
            format='mp3',
            tags={
                'artist': author,
                'title': title})
        duration = round(chapter.duration_seconds)
        length = os.stat(CHAPTERS_PATH + filename).st_size

        # generate markdown text and write to post
        markdown = '''---\nlayout: chapter\ntitle: "%s"\nauthor: %s\ndescription: %s\ndate: %s\nlength: %d\nduration: %d\nguid: %s\n---''' % (
            title, author, url, dtz.strftime('%Y-%m-%d %H:%M:%S %Z'), length, duration, name)
        with open(POSTS_PATH + dtz.strftime('%Y-%m-%d-') + name + '.md', 'w') as f:
            f.write(markdown)

        # uncomment to process single post
        # break
        num += 1

    # return 0 if chapters added, otherwise 1
    sys.exit(0 if num else 1)
