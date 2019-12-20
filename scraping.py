import urllib.request
from html.parser import HTMLParser
from html.entities import name2codepoint
from janome.tokenizer import Tokenizer

url = 'https://hellokoding.com/crud-restful-apis-with-go-modules-wire-gin-gorm-and-mysql/'

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
                print(attr, (attr[0] == 'name' or attr[0] == 'property') and 'description' in attr[1].lower())
                if (attr[0] == 'name' or attr[0] == 'property') and 'description' in attr[1].lower() and len(self.return_value) == 0:
                    print("     attr:", attr)
                    self.flag = True
                    # if len(self.content_value) > 0:
                    #     self.return_value = attr[1]
                elif attr[0] == 'content':
                    if self.flag:
                        # print(attr[1])
                        self.flag = False
                        self.return_value = attr[1]
                    # self.content_value = atstr[1]

    # def handle_data(self, data):
    #     if self.flag:
    #         # print(data)
    #         self.flag = False
    #         self.return_value = data

titleParser = TitleParser()
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
titleParser.feed(body)
title = titleParser.return_value
titleParser.close()
print(title)
for token in Tokenizer().tokenize(title):
    # print(token)
    part_of_speech_list = token.part_of_speech.split(',')
    hinsi = part_of_speech_list[0]
    hinsi_detail = part_of_speech_list[1]
    if hinsi == '名詞' and (hinsi_detail == '一般' or hinsi_detail == '固有名詞') and len(hinsi) > 1:
        print(token.surface)
        print(token.part_of_speech)

descriptionParser = DescriptionParser()
descriptionParser.feed(body)
description = descriptionParser.return_value
print(description)