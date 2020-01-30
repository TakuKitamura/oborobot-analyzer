# import urllib.request
import requests
from janome.tokenizer import Tokenizer
import pymongo
import time
import re
import nltk
from nltk.stem import WordNetLemmatizer
import unicodedata
from bs4 import BeautifulSoup
from bs4.element import Comment
from SPARQLWrapper import SPARQLWrapper, JSON
import random
import json
from googletrans import Translator

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
        only_english = re.compile('[a-zA-Zａ-ｚＡ-Ｚ -]+')
        for v in tagged:
            if len(v[0]) >= 3 and only_english.fullmatch(v[0]) != None:
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

def is_japanese(string):
    for ch in string:
        name = unicodedata.name(ch)
        if "CJK UNIFIED" in name \
        or "HIRAGANA" in name \
        or "KATAKANA" in name:
            return True
    return False

def get_ja_text_from_en(search_value):
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery("""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?label
        WHERE {{ <http://dbpedia.org/resource/{}> rdfs:label ?label }}
    """.format(search_value))

    # sparql = SPARQLWrapper("http://ja.dbpedia.org/sparql")
    # sparql.setQuery("""
    #     PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    #     SELECT ?label
    #     WHERE { <http://ja.dbpedia.org/resource/HTTP> rdfs:label ?label }
    # """)

    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    # pprint.pprint(ressults)
    # print(results)
    ja_value = ''
    # en_value = ''
    for result in results["results"]["bindings"]:
        # print()
        label = result['label']
        # print(label["xml:lang"], label["value"])
        if label["xml:lang"] == 'ja':
            ja_value = label["value"].split(' ')
            if len(ja_value) > 1:
                ja_value = ja_value[0]
            else:
                ja_value = label["value"]

    return ja_value

client = pymongo.MongoClient("localhost", 27017)
db = client.oborobot
# tokennizer = Tokenizer('neologd')
tokennizer = Tokenizer()

for obj in db.query.find({'is_checked': False}):
    try:
        url = obj['href']

        # headers = { "User-Agent" :  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36" }
        # req = urllib.request.Request(url, None, headers)
        # with urllib.request.urlopen(req) as res:
        #     # print(res.headers.get_content_charset())
        #     read_body = res.read()
        #     try:
        #         body = read_body.decode('utf-8')
        #     except:
        #         body = read_body.decode('shift-jis')

        # response = requests.get(url, headers=headers)
        # response.encoding = response.apparent_encoding
        # soup = BeautifulSoup(response.text, 'lxml')

        # web_text = text_from_html(response.text)

        lang = ''
        if is_japanese(obj['search_value']):
            lang = 'ja'
        else:
            lang = 'en'

        query_words = get_words(tokennizer, obj['search_value'], lang)

        # print("query_words=", query_words)

        for v in query_words['noun']:
            if len(v) == 0:
                continue
            upper_value = v.upper()
            first_char_upper = v[0].upper() + v[1:]
            if lang == 'en':
                is_translated = False
                ja_text = ''
                for objj in db.word.find({'jp_nickname': {'$ne' : ''}, 'lang': 'en'}):
                    if (objj['value'][0].upper() + objj['value'][1:]) == first_char_upper:
                        is_translated = True
                        ja_text = objj['jp_nickname']
                        break
                if is_translated == False:
                    get_ja_text = get_ja_text_from_en(first_char_upper)
                    time.sleep(1)
                    if get_ja_text != '':
                        ja_text = get_ja_text
                    else:
                        ja_text = v

                result=db.word.insert_one({'section_name': 'query', 'type': 'Noun', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': ja_text})
            else:
                result=db.word.insert_one({'section_name': 'query', 'type': 'Noun', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else first_char_upper})

        for v in query_words['properNoun']:
            if len(v) == 0:
                continue
            upper_value = v.upper()
            first_char_upper = v[0].upper() + v[1:]
            if lang == 'en':
                is_translated = False
                ja_text = ''
                for objj in db.word.find({'jp_nickname': {'$ne' : ''}, 'lang': 'en'}):
                    if (objj['value'][0].upper() + objj['value'][1:]) == first_char_upper:
                        is_translated = True
                        ja_text = objj['jp_nickname']
                        break
                if is_translated == False:
                    get_ja_text = get_ja_text_from_en(first_char_upper)
                    time.sleep(1)
                    if get_ja_text != '':
                        ja_text = get_ja_text
                    else:
                        ja_text = v

                result=db.word.insert_one({'section_name': 'query', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': ja_text})
            else:
                result=db.word.insert_one({'section_name': 'query', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else first_char_upper})

        for v in query_words['verb']:
            if len(v) == 0:
                continue
            upper_value = v.upper()
            first_char_upper = v[0].upper() + v[1:]
            if lang == 'en':
                result=db.word.insert_one({'section_name': 'query', 'type': 'Verb', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else first_char_upper})
            else:
                result=db.word.insert_one({'section_name': 'query', 'type': 'Verb', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else first_char_upper})

        for v in query_words['adjective']:
            if len(v) == 0:
                continue
            upper_value = v.upper()
            first_char_upper = v[0].upper() + v[1:]
            if lang == 'en':
                result=db.word.insert_one({'section_name': 'query', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else first_char_upper})
            else:
                result=db.word.insert_one({'section_name': 'query', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else first_char_upper})

        result = db.favorite.update_one({'_id':obj['_id']}, {"$set": {'is_checked': True}})
    except:
        print("for obj in db.query.find({'is_checked': False}): error")
        print("obj: ", obj)
        continue

for obj in db.favorite.find({'is_checked': False}):
    try:
        url = obj['href']

        headers = { "User-Agent" :  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36" }
        # req = urllib.request.Request(url, None, headers)
        # with urllib.request.urlopen(req) as res:
        #     # print(res.headers.get_content_charset())
        #     read_body = res.read()
        #     try:
        #         body = read_body.decode('utf-8')
        #     except:
        #         body = read_body.decode('shift-jis')

        # soup = BeautifulSoup(body, 'lxml')

        # web_text = text_from_html(body)
        # print(web_text)

        try:
            response = requests.get(url, headers=headers)
        except:
            continue
        time.sleep(1)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'lxml')

        web_text = text_from_html(response.text)

        title = ''
        title_soup = soup.find("meta", property="og:title")
        if title_soup != None:
            title = title_soup["content"]
        else:
            title = soup.find('title').text

        lang = ''
        if is_japanese(title):
            lang = 'ja'
        else:
            lang = 'en'

        description = ''
        description_soup = soup.find("meta",  property="og:description")
        if description_soup != None:
            description = description_soup["content"]
        else:
            description_soup = soup.find("meta",  property="description")
            if description_soup != None:
                description = description_soup["content"]
            else:
                if lang == 'ja':
                    description = web_text[0:120]
                else:
                    description = web_text[0:280]

        favorite_id = obj['_id']
        result = db.favorite.update({'_id': favorite_id}, {'$set':{'title':title, 'description': description}})
        title_words = get_words(tokennizer, title + description, lang)

        # descriptionParser = DescriptionParser()
        # descriptionParser.feed(body)
        # description = descriptionParser.return_value
        # descriptionParser.close()
        # print(description)
        description_words = get_words(tokennizer, description, lang)

        # print("title_words=", title_words)
        # print("description_words=", description_words)

        for v in title_words['noun']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    first_char_upper = v[0].upper() + v[1:]
                    is_translated = False
                    ja_text = ''
                    for objj in db.word.find({'jp_nickname': {'$ne' : ''}, 'lang': 'en'}):
                        if (objj['value'][0].upper() + objj['value'][1:]) == first_char_upper:
                            is_translated = True
                            ja_text = objj['jp_nickname']
                            break
                    if is_translated == False:
                        get_ja_text = get_ja_text_from_en(first_char_upper)
                        time.sleep(1)
                        if get_ja_text != '':
                            ja_text = get_ja_text
                        else:
                            ja_text = v
                    result=db.word.insert_one({'section_name': 'title', 'type': 'Noun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': ja_text})
                else:
                    result=db.word.insert_one({'section_name': 'title', 'type': 'Noun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in title_words['properNoun']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    first_char_upper = v[0].upper() + v[1:]
                    is_translated = False
                    ja_text = ''
                    for objj in db.word.find({'jp_nickname': {'$ne' : ''}, 'lang': 'en'}):
                        if (objj['value'][0].upper() + objj['value'][1:]) == first_char_upper:
                            is_translated = True
                            ja_text = objj['jp_nickname']
                            break
                    if is_translated == False:
                        get_ja_text = get_ja_text_from_en(first_char_upper)
                        time.sleep(1)
                        if get_ja_text != '':
                            ja_text = get_ja_text
                        else:
                            ja_text = v

                    result=db.word.insert_one({'section_name': 'title', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': ja_text})
                else:
                    result=db.word.insert_one({'section_name': 'title', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in title_words['verb']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    result=db.word.insert_one({'section_name': 'title', 'type': 'Verb', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})
                else:
                    result=db.word.insert_one({'section_name': 'title', 'type': 'Verb', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in title_words['adjective']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    result=db.word.insert_one({'section_name': 'title', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})
                else:
                    result=db.word.insert_one({'section_name': 'title', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in description_words['noun']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    result=db.word.insert_one({'section_name': 'description', 'type': 'Noun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})
                else:
                    result=db.word.insert_one({'section_name': 'description', 'type': 'Noun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in description_words['properNoun']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    result=db.word.insert_one({'section_name': 'description', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})
                else:
                    result=db.word.insert_one({'section_name': 'description', 'type': 'ProperNoun', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in description_words['verb']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    result=db.word.insert_one({'section_name': 'description', 'type': 'Verb', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})
                else:
                    result=db.word.insert_one({'section_name': 'description', 'type': 'Verb', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        for v in description_words['adjective']:
            upper_value = v.upper()
            web_text_upper = web_text.upper()
            if (web_text_upper.count(upper_value) > 0):
                if lang == 'en':
                    result=db.word.insert_one({'section_name': 'description', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})
                else:
                    result=db.word.insert_one({'section_name': 'description', 'type': 'Adjective', 'lang': lang, 'href': url, 'count': web_text_upper.count(upper_value), 'value': v, 'upper_value': upper_value, 'jp_nickname': '' if is_japanese(v) else v})

        result = db.favorite.update_one({'_id':obj['_id']}, {"$set": {'is_checked': True}})

        time.sleep(1)
    except:
        print("for obj in db.query.favorite({'is_checked': False}): error")
        print("obj: ", obj)
        time.sleep(1)
        continue

"""


config_file = open('config.json', 'r')
config  = json.load(config_file)

translator = Translator()

client = pymongo.MongoClient("localhost", 27017)
db = client.oborobot

def include_hiragana(word):
    kana_set = {chr(i) for i in range(12353, 12436)}
    word_set = set(word)
    if kana_set - word_set == kana_set:
        return False
    else:
        return True

def request_yandex_translater(text):
    url = "https://translate.yandex.net/api/v1.5/tr.json/translate?key={}&text={}&lang=ja-en".format(config['yandex_key'], text)
    res = requests.get(url)
    res_json = json.loads(res.text)
    if res_json['code'] != 200:
        return ''
    else:
        return res_json['text'][0]

def request_googletrans(text):
    return translator.translate(text, src='ja' ,dest='en').text

def gen_question(question_seed, hinsiType):
    translated_from_ja_to_en = ''
    question_seed_en = question_seed['en']
    question_seed_ja = question_seed['ja']

    # question_seed_type = -1
    # if len(question_seed_en) == 0:
    #     question_seed_type = 1
    # elif len(question_seed_ja) == 0:
    #     question_seed_type = 2
    # else:
    #     question_seed_type = 3

    if len(question_seed_en) == 0:
        question_result = list(db.question.find({'question_seed_ja': question_seed_ja}))
        if len(question_result) == 0:
            random_value = random.randint(1,2)
            random_interval = random.randint(1,3)
            try:
                if random_value == 1:
                    translated_from_ja_to_en = request_yandex_translater(question_seed_ja)
                    if len(translated_from_ja_to_en) == 0:
                        translated_from_ja_to_en = request_googletrans(question_seed_ja)
                else:
                    translated_from_ja_to_en = request_googletrans(question_seed_ja)
                    if len(translated_from_ja_to_en) == 0:
                        translated_from_ja_to_en = request_yandex_translater(question_seed_ja)
            except:
                try:
                    translated_from_ja_to_en = request_yandex_translater(question_seed_ja)
                except:
                    print('translate error')
                    return
            time.sleep(random_interval)
        else:
            translated_from_ja_to_en = question_result[0]['translated_from_ja_to_en']

        # print('AAA')
            # result=db.question.insert_one({'question': , 'lang': lang, 'href': url, 'count': -1, 'value': v, 'upper_value': upper_value, 'jp_nickname': ja_text})

    ja_question = ''
    en_question = ''

    # if len(question_seed_en) == 0: 日本語
    #     question_seed_type = 1
    # elif len(question_seed_ja) == 0: 英語
    #     question_seed_type = 2
    # else: 日本語 英語
    #     question_seed_type = 3

    if hinsiType == 'ProperNoun':
        if len(question_seed_en) == 0:# 日本語
            ja_question = 'それは ' + question_seed_ja + ' に関係する?'
            en_question = 'Do you think it is related to "' + translated_from_ja_to_en + '"?'
        elif len(question_seed_ja) == 0:# 英語
            ja_question = 'それは ' + question_seed_en + ' に関係する?'
            en_question = 'Do you think it is related to "' + question_seed_en + '"?'
        else:# 日本語 英語
            ja_question = 'それは ' + question_seed_ja + ' に関係する?'
            en_question = 'Do you think it is related to "' + question_seed_en + '"?'

    elif hinsiType == 'Noun':
        if len(question_seed_en) == 0:# 日本語
            ja_question = 'それは ' + question_seed_ja + ' に関係しそう?'
            en_question = 'Do you think it is related to "' + translated_from_ja_to_en + '"?'
        elif len(question_seed_ja) == 0:# 英語
            ja_question = 'それは ' + question_seed_en + ' に関係しそう?'
            en_question = 'Do you think it is related to "' + question_seed_en + '"?'
        else:# 日本語 英語
            ja_question = 'それは ' + question_seed_ja + ' に関係しそう?'
            en_question = 'Do you think it is related to "' + question_seed_en + '"?'
    elif hinsiType == 'Adjective':
        if len(question_seed_en) == 0:# 日本語
            ja_question = 'それに対して ' + question_seed_ja + ' なイメージがある?'
            en_question = 'Do you have a "' + translated_from_ja_to_en + '" image for that?'
        elif len(question_seed_ja) == 0:# 英語
            ja_question = 'それに対して ' + question_seed_en + ' なイメージがある?'
            en_question = 'Do you have a "' + question_seed_en + '" image for that?'
        else:# 日本語 英語
            ja_question = 'それに対して ' + question_seed_ja + ' なイメージがある?'
            en_question = 'Do you have a "' + question_seed_en + '" image for that?'
    elif hinsiType == 'Verb':
        if len(question_seed_en) == 0:# 日本語
            ja_question = 'それは ' + question_seed_ja + ' に関係する?'
            en_question = 'Do you think it is related to "' + translated_from_ja_to_en + '"?'
        elif len(question_seed_ja) == 0:# 英語
            ja_question = 'それは ' + question_seed_en + ' に関係する?'
            en_question = 'Do you think it is related to "' + question_seed_en + '"?'
        else:# 日本語 英語
            ja_question = 'それは ' + question_seed_ja + ' に関係する?'
            en_question = 'Do you think it is related to "' + question_seed_en + '"?'
        # ja_question = 'それは ' + question_seed + ' ことに関係する?' if include_hiragana(question_seed) else 'それは何かの ' + question_seed + ' に関係する?'

        # if len(translated_from_ja_to_en) == 0:
        #     en_question = 'Do you think it is related to "' + question_seed + '"?'
        # else:
        #     en_question ='Do you think it is related to "' + translated_from_ja_to_en + '"?'
    else:
        print('unknown hinsiType')
        return

    # # TODO: ここの構造は見直し
    # if len(list(db.question.find({'question': ja_question}))) == 0:
    #     result=db.question.insert_one({'question': ja_question, 'lang': 'ja', 'question_seed_en': question_seed_en,  'question_seed_ja': question_seed_ja, 'question_seed_type' : hinsiType ,'translated_from_ja_to_en': translated_from_ja_to_en})
    #     # print('BBB')

    # if len(list(db.question.find({'question': en_question}))) == 0:
    #     result=db.question.insert_one({'question': en_question, 'lang': 'en', 'question_seed_en': question_seed_en,  'question_seed_ja': question_seed_ja, 'question_seed_type' : hinsiType ,'translated_from_ja_to_en': ''})
    #     # print('CCC')

    # TODO: ここの構造は見直し
    if len(list(db.question.find({'question_ja': ja_question}))) == 0 and len(list(db.question.find({'question_en': en_question}))) == 0:
        result=db.question.insert_one({'question_ja': ja_question, 'question_en': en_question, 'question_seed_en': question_seed_en,  'question_seed_ja': question_seed_ja, 'question_seed_type' : hinsiType ,'translated_from_ja_to_en': translated_from_ja_to_en})
        # print('BBB')

    # if len(list(db.question.find({'question': en_question}))) == 0:
    #     result=db.question.insert_one({'question': en_question, 'lang': 'en', 'question_seed_en': question_seed_en,  'question_seed_ja': question_seed_ja, 'question_seed_type' : hinsiType ,'translated_from_ja_to_en': ''})
    #     # print('CCC')

    # print('DDD')


def remove_duplication(hinsi_list):
    upper_key_list = {}
    for v in list(set(hinsi_list)):
        upper_key_list[v.upper()] = v.lower()

    r = []
    for key in upper_key_list:
        r.append(upper_key_list[key])

    return r

for obj in db.word.find({"type": "ProperNoun"}):
    if obj['jp_nickname'] == '':
        gen_question({'en': '', 'ja': obj['value']}, 'ProperNoun') # 日本語,
    else:
        if obj['value'] != obj['jp_nickname']:
            gen_question({'en': obj['value'], 'ja': obj['jp_nickname']}, 'ProperNoun') # 英語, 日本語
        else:
            gen_question({'en': obj['value'], 'ja': ''}, 'ProperNoun') # 英語,

for obj in db.word.find({"type": "Noun"}):
    if obj['jp_nickname'] == '':
        gen_question({'en': '', 'ja': obj['value']}, 'Noun') # 日本語,
    else:
        if obj['value'] != obj['jp_nickname']:
            gen_question({'en': obj['value'], 'ja': obj['jp_nickname']}, 'Noun') # 英語, 日本語
        else:
            gen_question({'en': obj['value'], 'ja': ''}, 'Noun') # 英語,

for obj in db.word.find({"type": "Adjective"}):
    if obj['jp_nickname'] == '':
        gen_question({'en': '', 'ja': obj['value']}, 'Adjective') # 日本語,
    else:
        if obj['value'] != obj['jp_nickname']:
            gen_question({'en': obj['value'], 'ja': obj['jp_nickname']}, 'Adjective') # 英語, 日本語
        else:
            gen_question({'en': obj['value'], 'ja': ''}, 'Adjective') # 英語,

for obj in db.word.find({"type": "Verb"}):
    if obj['jp_nickname'] == '':
        gen_question({'en': '', 'ja': obj['value']}, 'Verb') # 日本語,
    else:
        if obj['value'] != obj['jp_nickname']:
            gen_question({'en': obj['value'], 'ja': obj['jp_nickname']}, 'Verb') # 英語, 日本語
        else:
            gen_question({'en': obj['value'], 'ja': ''}, 'Verb') # 英語,

""";