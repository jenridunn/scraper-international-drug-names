from bs4 import BeautifulSoup
import requests
import time
import pandas as pd
from selenium import webdriver
from tqdm import tqdm
import sqlite3


class IntMedsScrapper:
    def __init__(self, letter, database):
        self.letter = letter
        self.database = self.database

    def createDynamicUrlsL0(self):
        driver = webdriver.Chrome()
        root_url_part1 = 'https://www.drugs.com/international-'
        root_url_part2 = '.html'
        driver.get(root_url_part1+self.letter+'1'+root_url_part2)
        time.sleep(3)
        html = BeautifulSoup(driver.page_source, 'html.parser')
        try:
            pages = len(html.find('ul', {
                        'class': 'ddc-paging ddc-paging-result ddc-paging-sitemap-1 list-length-long list-type-word'}).findAll('li'))
        except:
            try:
                pages = len(html.find('ul', {
                            'class': 'ddc-paging ddc-paging-result ddc-paging-sitemap-1 list-length-medium list-type-word'}).findAll('li'))
            except:
                try:
                    pages = len(html.find('ul', {
                                'class': 'ddc-paging ddc-paging-result ddc-paging-sitemap-1 list-length-short list-type-word'}).findAll('li'))
                except:
                    try:
                        pages = len(html.find('ul', {
                            'class': 'ddc-list-column-2 sitemap-list'}).findAll('li'))
                    except:
                        try:
                            pages = len(html.find('ul', {
                                        'class': 'ddc-paging ddc-paging-result ddc-paging-sitemap-1'}).findAll('li'))
                        except Exception as e:
                            print(f'ERROR IN createDynamicUrlsL0 - {e}')

        urls = []
        for i in range(1, pages):
            urls.append(root_url_part1+self.letter+str(i)+root_url_part2)
        driver.quit()
        return urls

    def extractUrlMedicationsL1(self, urls):
        driver = webdriver.Chrome()
        medsUrls = []
        print(f'Medications Pages - Letter {self.letter.upper()}')
        classL1_options = [
            'ddc-list-column-2 list-length-long list-type-word',
            'ddc-list-column-2 sitemap-list list-length-long list-type-word',
            'ddc-list-column-2 sitemap-list list-length-medium list-type-word',
            'ddc-list-column-2 sitemap-list list-length-short list-type-word',
            'ddc-list-column-2 sitemap-list list-length-long list-type-paragraph',
            'ddc-list-column-2 sitemap-list list-length-medium list-type-paragraph',
            'ddc-list-column-2 sitemap-list list-length-short list-type-paragraph',
        ]
        for i in range(0, len(urls)):
            driver.get(urls[i])
            time.sleep(4)
            html = BeautifulSoup(driver.page_source, 'html.parser')
            found_it = False
            try:
                for classL1It in range(0, len(classL1_options)+1):
                    while found_it == False:
                        try:
                            meds = html.find('ul', {
                                'class': classL1_options[classL1It]}).findAll('li')
                            found_it = True
                        except:
                            continue
            except Exception as e:
                print(f'ERROR extractUrlMedicationsL1 {urls[i]} --- {e}')

            for med in meds:
                medsUrls.append(med.find('a')['href'])

            print(
                f'Medications Pages Processed {i+1}/{len(urls)} - Letter {self.letter.upper()}')
        driver.quit()
        return medsUrls

    def extractActiveSubsL2(self, links):
        medName = []
        textIngreds = []
        urlIngreds = []
        contentBoxHtml = []
        for i in tqdm(range(0, len(links))):
            res = requests.get('https://www.drugs.com'+links[i])
            time.sleep(2)
            html = BeautifulSoup(res.content, 'html.parser')
            try:
                ingreds = html.findAll('h3')
                contentBoxHtml.append(str(html).split('<!-- google_ad_section_start -->')[1].split(
                    '<!-- google_ad_section_end -->')[0].split('<p class="no-ad">')[0].replace('\n', ''))
                try:
                    getTextIngreds = [i.find('a').text for i in ingreds]
                except:
                    ingreds = html.findAll('h1')
                    getTextIngreds = [i.text for i in ingreds]
                textIngreds.append(','.join(getTextIngreds))
                try:
                    urlIngredsPrev = [i.find('a')['href'] for i in ingreds]
                except:
                    urlIngredsPrev = str(
                        [links[i].replace('https://www.drugs.com', '')])
                urlIngreds.append(str(urlIngredsPrev))
                medName.append(html.find('h1').text)
            except Exception as e:
                print(
                    f'ERROR CHECK OUT THIS URL: {"https://www.drugs.com"+links[i]} --- {e}')
        return (links, medName, textIngreds, urlIngreds, contentBoxHtml)

    def updateDB(self):
        conn = sqlite3.connect(self.database)
        c = conn.cursor()
        for index, row in self.medsInfoDF.iterrows():
            c.execute(f'INSERT INTO data VALUES (:MEDICATION_NAME, :INGREDIENTS, :URL_INGREDIENTS, :MEDICATION_URL, :MEDICATION_CONTENTBOX_HTML)',
                      {"MEDICATION_NAME": row["MEDICATION_NAME"], "INGREDIENTS": row["INGREDIENTS"], "URL_INGREDIENTS": row["URL_INGREDIENTS"], "MEDICATION_URL": row["MEDICATION_URL"], "MEDICATION_CONTENTBOX_HTML": row["MEDICATION_CONTENTBOX_HTML"]})
        conn.commit()
        conn.close()

    def executor(self):
        self.medsInfoDF = pd.DataFrame({'MEDICATION_NAME': [], 'INGREDIENTS': [
        ], 'URL_INGREDIENTS': [], 'MEDICATION_CONTENTBOX_HTML': []})
        urls = self.createDynamicUrlsL0()
        medsUrls = self.extractUrlMedicationsL1(urls)
        links, medName, textIngreds, urlIngreds, contentBoxHtml = self.extractActiveSubsL2(
            medsUrls)
        index = 0
        for v, x, y, z, a in zip(links, medName, textIngreds, urlIngreds, contentBoxHtml):
            medsInfoDF.loc[index, 'MEDICATION_NAME'] = x
            medsInfoDF.loc[index, 'INGREDIENTS'] = y
            medsInfoDF.loc[index, 'URL_INGREDIENTS'] = z
            medsInfoDF.loc[index, 'MEDICATION_URL'] = v
            medsInfoDF.loc[index, 'MEDICATION_CONTENTBOX_HTML'] = a
            index += 1
        medsInfoDF.to_csv(f'letter{self.letter.upper()}.csv')
        self.updateDB()
        return '----------- SCRAPING DONE-------------'
