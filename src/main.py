import os
import logging
import requests
import textwrap
from dotenv import load_dotenv
from pymongo import MongoClient
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import selenium

from selenium.webdriver import ChromeOptions, Remote
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchAttributeException
from time import sleep

def get_joke(url):
    
    request = requests.get(url)
    if request.status_code != 200:
        raise Exception("HTTP CALL FAILED")
    
    return request.json()

def is_joke_in_db(id, mongo_client):
    
    result = mongo_client.jokes.find_one({'joke_id': id})
    return (True if result else False) 

def add_joke_to_database(id, mongo_client):
    
    result = mongo_client.jokes.insert_one({'joke_id': id})
    return result.inserted_id

def prepare_joke(joke, size=35):

    lines = textwrap.wrap(joke, size,  break_long_words=False)
    return "\n".join(lines)

def generate_image(joke, watermark='@boobiestabubies', size=(1080, 1080), font_color=(255, 255, 0), font_path="./src/font/Monerd-Bold.ttf", background_color='blue'):
    
    font = ImageFont.truetype(BytesIO(open(font_path, "rb").read()), size=72)
    watermark_font = ImageFont.truetype(BytesIO(open(font_path, "rb").read()), size=32)
    
    img = Image.new('RGB', size, color=background_color)
    img_draw = ImageDraw.Draw(img)

    textWidth, textHeight = img_draw.textsize(joke, font=font)
    xText = (size[0] - textWidth) / 2
    yText = (size[1] - textHeight) / 2

    img_draw.text((xText, yText), joke, font=font, fill=font_color)
    img_draw.text((870, 1040), watermark, font=watermark_font, fill=font_color)
    return img


def setup_browser():
    options = ChromeOptions()
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')

    return Remote(
        command_executor=os.getenv("SELENIUM_CONTAINER"),
        options=options
    )

def upload_to_ig(browser, username, password, image_path, caption):
    browser.get("https://instagram.com")
    
    sleep(10)
    try:
        button = browser.find_element(by=By.XPATH, value="/html/body/div[4]/div/div/button[1]")
        button.click()
    except NoSuchAttributeException as e:
        logging.error(e)

    sleep(5)
    username_input = browser.find_element(by=By.XPATH, value="/html/body/div[1]/section/main/article/div[2]/div[1]/div[2]/form/div/div[1]/div/label/input")
    username_input.send_keys(username)

    password_input = browser.find_element(by=By.XPATH, value="/html/body/div[1]/section/main/article/div[2]/div[1]/div[2]/form/div/div[2]/div/label/input")
    password_input.send_keys(password)

    sleep(2)
    login_button = browser.find_element(by=By.XPATH, value="/html/body/div[1]/section/main/article/div[2]/div[1]/div[2]/form/div/div[3]/button")
    login_button.click()

    sleep(10)
    upload_button = browser.find_element(by=By.XPATH, value="/html/body/div[1]/section/nav/div[2]/div/div/div[3]/div/div[3]/div/button")
    upload_button.click()

    sleep(2)
    drop_element = browser.find_element(by=By.XPATH, value="/html/body/div[8]/div[2]/div/div/div/div[2]/div[1]/form/input")
    drop_element.send_keys(image_path)
    
    sleep(10)
    next_button = browser.find_element(by=By.XPATH, value="/html/body/div[6]/div[2]/div/div/div/div[1]/div/div/div[3]/div/button")
    next_button.click()

    sleep(5)
    next_button2 = browser.find_element(by=By.XPATH, value="/html/body/div[6]/div[2]/div/div/div/div[1]/div/div/div[3]/div/button")
    next_button2.click()

    sleep(5)
    caption_area = browser.find_element(by=By.XPATH, value="/html/body/div[6]/div[2]/div/div/div/div[2]/div[2]/div/div/div/div[2]/div[1]/textarea")
    caption_area.send_keys(caption)

    sleep(5)
    share_button = browser.find_element(by=By.XPATH, value="/html/body/div[6]/div[2]/div/div/div/div[1]/div/div/div[3]/div/button")
    share_button.click()

    sleep(2)
    browser.close()

def main():
    load_dotenv()

    # get joke
    joke = get_joke(os.getenv("URL"))
    logging.info("got joke")

    # check if joke is already in database
    client = MongoClient(os.getenv("MONGO_URL")).chucky
    if not is_joke_in_db(joke['id'], client):
        logging.info("joke not found in db")

        add_joke_to_database(joke['id'], client)
        logging.info("added joke to db")

        # generate image
        image = generate_image(prepare_joke(joke['value']))

        img_path = "./media/tempimg.jpeg"
        with open(img_path, "w") as save_file:
            image.save(save_file)
        
        logging.info("saved image")
        
        # send image to instagram
        caption = """ What is your favorite Chuck Norris Joke ?
        Write it down in the commends and tag a mate - Like for more!
        
        #chucknorris #chucknorrisjokes
        """

        browser = setup_browser()
        upload_to_ig(browser, os.getenv("IG_USER"), os.getenv("IG_PASSWD"), img_path, caption)
        logging.info("uploaded to ig")

    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()