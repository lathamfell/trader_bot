import requests
from bs4 import BeautifulSoup


def main():
    # connect to site
    URL = "https://icanhas.cheezburger.com/lolcats"
    page = requests.get(URL)
    print(page.text)

    # scrape contents
    soup = BeautifulSoup(page.content, "html.parser")


    # filter contents



    # download cat contents
    image_url = "https://i.chzbgr.com/original/9667550208/hFC1DC6A3/cheezburger-image-9667550208"
    img_data = requests.get(image_url).content
    with open('image1.jpg', 'wb') as handler:
        handler.write(img_data)


if __name__ == "__main__":
    main()
