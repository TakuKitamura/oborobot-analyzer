import urllib.request
from html.parser import HTMLParser
from html.entities import name2codepoint
from janome.tokenizer import Tokenizer
import pymongo
import time
import re
import nltk
from nltk.stem import WordNetLemmatizer

class TitleParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.return_value = ""
        self.flag = False # タイトルタグの場合のフラグ

    def handle_starttag(self, tag, attrs):
        if (tag == "title"):
            self.flag = True

    def handle_data(self, data):
        if self.flag:
            self.flag = False
            self.return_value = data

class DescriptionParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.return_value = ""
        # self.content_value = ""
        self.flag = False # タイトルタグの場合のフラグ

    def handle_starttag(self, tag, attrs):
        if (tag == "meta"):
            for attr in attrs:
                # print(attr, (attr[0] == 'name' or attr[0] == 'property') and 'description' in attr[1].lower())
                if (attr[0] == 'name' or attr[0] == 'property') and 'description' in attr[1].lower() and len(self.return_value) == 0:
                    # print("     attr:", attr)
                    self.flag = True
                    # if len(self.content_value) > 0:
                    #     self.return_value = attr[1]
                elif attr[0] == 'content':
                    if self.flag:
                        # print(attr[1])
                        self.flag = False
                        self.return_value = attr[1]
                    # self.content_value = atstr[1]

class LangParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.return_value = ""
        # self.content_value = ""
        # self.flag = False # タイトルタグの場合のフラグ

    def handle_starttag(self, tag, attrs):
        if (tag == "html"):
            for attr in attrs:
                # print(attr, (attr[0] == 'name' or attr[0] == 'property') and 'description' in attr[1].lower())
                if attr[0] == 'lang':
                    # print("     attr:", attr)
                    # self.flag = True
                    self.return_value = attr[1]

def get_meisi(tokennizer, data, lang):
    ippan = []
    koyuu = []
    sahen = []
    if lang == 'ja':
        for token in tokennizer.tokenize(data):
            # print(token)
            part_of_speech_list = token.part_of_speech.split(',')
            hinsi = part_of_speech_list[0]
            hinsi_detail = part_of_speech_list[1]
            # print(token)
            code_regex = re.compile('[!"#$%&\'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]')

            if hinsi == '名詞' and code_regex.match(token.surface) == None:
                if hinsi_detail == '一般':
                    ippan.append(token.surface)
                elif hinsi_detail == '固有名詞':
                    koyuu.append(token.surface)
                elif hinsi_detail == 'サ変接続':
                    sahen.append(token.surface)
                # print(token.surface)s
        return {"ippan": ippan, "koyuu": koyuu, "sahen": sahen}
    elif lang == 'en':
        tokens = nltk.word_tokenize(data)
        tagged = nltk.pos_tag(tokens)
        lemmatizer = WordNetLemmatizer()
        for v in tagged:
            if v[1] == 'NN' or v[1] == 'NNS':
                ippan.append(lemmatizer.lemmatize(v[0], 'n'))
            elif v[1] == 'NNP' or v[1] == 'NNPS':
                koyuu.append(lemmatizer.lemmatize(v[0], 'n'))
            elif v[1] == 'VB' or v[1] == 'VBD' or v[1] == 'VBG' or v[1] == 'VBN' or v[1] == 'VBP' or v[1] == 'VBZ':
                sahen.append(lemmatizer.lemmatize(v[0], 'v'))

        return {"ippan": ippan, "koyuu": koyuu, "sahen": sahen}
    else:
        return {}



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
    # print(body)
    # a

    # langParser = LangParser()
    # langParser.feed(body)
    # lang = langParser.return_value
    # langParser.close()
    # print(lang)

    titleParser = TitleParser()
    titleParser.feed(body)
    title = titleParser.return_value
    titleParser.close()
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
    title_meisi = get_meisi(tokennizer, title, lang)

    descriptionParser = DescriptionParser()
    descriptionParser.feed(body)
    description = descriptionParser.return_value
    descriptionParser.close()
    # print(description)
    description_meisi = get_meisi(tokennizer, description, lang)

    print("title_meisi=", title_meisi)
    print("description_meisi=", description_meisi)
    time.sleep(2)