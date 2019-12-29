from selenium import webdriver
from selenium.webdriver.chrome.options import Options
options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.get('https://qiita.com/__init__/items/145462cdbb0f569a29cf')
page_width = driver.execute_script('return document.body.scrollWidth')
# page_height = driver.execute_script('return document.body.scrollHeight')
driver.set_window_size(page_width, 500)
driver.save_screenshot('screenshot.png')