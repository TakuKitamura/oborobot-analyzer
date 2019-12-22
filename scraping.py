import urllib.request
from janome.tokenizer import Tokenizer
import pymongo
import time
import re
import nltk
from nltk.stem import WordNetLemmatizer

from bs4 import BeautifulSoup
from bs4.element import Comment

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)
    return u" ".join(t.strip() for t in visible_texts)

def get_words(tokennizer, data, lang):
    noun = []
    properNoun = []
    verb = []
    adjective = []
    if lang == 'ja':
        for token in tokennizer.tokenize(data):
            # print(token)
            part_of_speech_list = token.part_of_speech.split(',')
            hinsi = part_of_speech_list[0]
            hinsi_detail = part_of_speech_list[1]
            # print(token)
            code_regex = re.compile('[!"#$%&\'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]')

            if hinsi == '名詞' and code_regex.match(token.base_form) == None and len(token.base_form) >= 2:
                if hinsi_detail == '一般':
                    noun.append(token.base_form)
                elif hinsi_detail == '固有名詞':
                    properNoun.append(token.base_form)
                elif hinsi_detail == 'サ変接続':
                    verb.append(token.base_form)
                elif hinsi_detail == '形容動詞語幹':
                    adjective.append(token.base_form)
            elif hinsi == '動詞' and code_regex.match(token.base_form) == None and len(token.base_form) >= 2:
                if hinsi_detail == '自立':
                    verb.append(token.base_form)
            elif hinsi == '形容詞' and code_regex.match(token.base_form) == None and len(token.base_form) >= 2:
                if hinsi_detail == '自立':
                    adjective.append(token.base_form)


                # print(token.surface)s
    elif lang == 'en':
        tokens = nltk.word_tokenize(data)
        tagged = nltk.pos_tag(tokens)
        lemmatizer = WordNetLemmatizer()
        for v in tagged:
            if len(v[0]) >= 3:
                if v[1] == 'NN' or v[1] == 'NNS':
                    noun.append(lemmatizer.lemmatize(v[0], pos='n'))
                elif v[1] == 'NNP' or v[1] == 'NNPS':
                    properNoun.append(lemmatizer.lemmatize(v[0], pos='n'))
                elif v[1] == 'VB' or v[1] == 'VBD' or v[1] == 'VBG' or v[1] == 'VBN' or v[1] == 'VBP' or v[1] == 'VBZ':
                    verb.append(lemmatizer.lemmatize(v[0], pos='v'))
                elif v[1] == 'JJ' or v[1] == 'JJR' or v[1] == 'JJS':
                    adjective.append(lemmatizer.lemmatize(v[0], pos="a"))
    else:
        pass

    return {"noun": noun, "properNoun": properNoun, "verb": verb, "adjective": adjective}



client = pymongo.MongoClient("localhost", 27017)
db = client.oborobot

tokennizer = Tokenizer('neologd')
for obj in db.favorite.find({'is_checked': False}):
    url = obj['href']

    headers = { "User-Agent" :  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36" }
    req = urllib.request.Request(url, None, headers)
    with urllib.request.urlopen(req) as res:
        # print(res.headers.get_content_charset())
        read_body = res.read()
        try:
            body = read_body.decode('utf-8')
        except:
            body = read_body.decode('shift-jis')

    soup = BeautifulSoup(body, 'lxml')

    web_text = text_from_html(body)

    title = ''
    title_soup = soup.find("meta", property="og:title")
    if title_soup != None:
        title = title_soup["content"]
    else:
        title = soup.find('title').text

    description = ''
    description_soup = soup.find("meta",  property="og:description")
    if description_soup != None:
        description = description_soup["content"]
    else:
        description_soup = soup.find("meta",  property="description")
        if description_soup != None:
            description = description_soup["content"]
        else:
            pass
    # print(body)
    # a

    # langParser = LangParser()
    # langParser.feed(body)
    # lang = langParser.return_value
    # langParser.close()
    # print(lang)
    # print(body)
    # titleParser = TitleParser()
    # titleParser.feed(body)
    # title = titleParser.return_value
    # titleParser.close()
    # print(tsitle)
    # for token in Tokenizer().tokenize(title):
    #     # print(token)
    #     part_of_speech_list = token.part_of_speech.split(',')
    #     hinsi = part_of_speech_list[0]
    #     hinsi_detail = part_of_speech_list[1]
    #     if hinsi == '名詞' and (hinsi_detail == '一般' or hinsi_detail == '固有名詞') and len(hinsi) > 1:
    #         print(token.surface)
    #         print(token.part_of_speech

    lang = obj['lang']
    title_words = get_words(tokennizer, title, lang)

    # descriptionParser = DescriptionParser()
    # descriptionParser.feed(body)
    # description = descriptionParser.return_value
    # descriptionParser.close()
    # print(description)
    description_words = get_words(tokennizer, description, lang)

    print("title_words=", title_words)
    print("description_words=", description_words)

    for v in title_words['noun']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'title', 'type': 'Noun', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    for v in title_words['properNoun']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'title', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    for v in title_words['verb']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'title', 'type': 'Verb', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    for v in title_words['adjective']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'title', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})


    for v in description_words['noun']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'description', 'type': 'Noun', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    for v in description_words['properNoun']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'description', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    for v in description_words['verb']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'description', 'type': 'Verb', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    for v in description_words['adjective']:
        if (web_text.count(v) > 0):
            result=db.word.insert_one({'section_name': 'description', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': web_text.count(v), 'value': v})

    result = db.favorite.update_one({'_id':obj['_id']}, {"$set": {'is_checked': True}})

    time.sleep(1)