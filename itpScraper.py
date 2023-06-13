from selenium import webdriver
import time
import re
import datetime
import os
from bs4 import BeautifulSoup
import numpy as np
import itp_creds
import pandas as pd
# from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
import pickle

# import seaborn as sns
# import matplotlib.pyplot as plt
# from collections import defaultdict
# from sklearn import metrics
# from sklearn.cluster import KMeans

## Create Filename:
def sub_all(pattern, sub_str, start_str):
    update = re.sub(pattern, sub_str, start_str)
    if update != start_str:
        #recurse!
        return sub_all(pattern, sub_str, update)
    else:
        return update

def snapshot_page_html(html, url):
    #Clean URL For SubFolder Creation
    cleaned_url = sub_all("[:/.]","-", cur_url.strip("https://"))
    
    #Get CWD
    root_dir = os.getcwd()
    
    #Create SubFolder (if Necessary)
    os.chdir(root_dir)
    if os.path.isdir(cleaned_url):
        os.chdir(cleaned_url)
    else:
        os.mkdir(cleaned_url)
        os.chdir(cleaned_url)
        
    #Record Snapshot Time
    time_now = datetime.datetime.now().strftime("%m-%d-%y_%H%M%p")
    
    #Create Filename
    filename = "WebPageSnapshot_{}.html".format(time_now)
    
    #Write HTML to File
    if os.path.isfile(filename):
        print("File already exists.")
        os.chdir(root_dir)
        return None
    with open(filename, "w") as f:
        f.write(cur_html)
        
    #Return to Original Directory
    os.chdir(root_dir)

def parse_session(session):
    session_title = session.find('a').text
    session_id = int(session.find('a').get('href').split('/')[-1])
    session_info = session.find(class_="sessionInfo").text
    session_leader = re.findall(".*Leaders:(.*)", session_info)[0].strip()
    session_time = session_info.split("\n")[1]
    session_right_column = session.find(class_="sessionRightColumn")
    session_tags = session_right_column.find(class_="sessionTags")
    sessionRSVPs = session_right_column.find(class_="sessionRSVPs")
    session_dict = {}
    session_dict['title'] = session_title
    session_dict['tags'] = [tag.text for tag in session_tags.find_all('a')]
    session_dict['popularity'] = re.findall("(\d*) RSVPs.*?", sessionRSVPs.text)
    session_dict['session_leader'] = session_leader
    session_dict['session_time'] = session_time
    session_dict['id'] = session_id
    return session_dict

def parse_user_sessions(driver):
    #Move Tabs
    sessions_attending_tab = driver.find_element_by_xpath("//div[@id='tabAttending']")
    sessions_attending_tab.click()
    
    time.sleep(np.random.uniform(1,4)) #Brief Pause
    sessions_attending_list = driver.find_element_by_xpath("//div[@id='calendarListAttending']") 
    user_sessions = []
    soup = BeautifulSoup(sessions_attending_list.get_attribute('innerHTML'),features="lxml")
    
    previous_sessions = soup.find(id="previousSessionsList")
    current_sessions = soup.find(id="currentSessionsList")
    
    sessions_list = previous_sessions.findAll("div", id=re.compile("sessionListID-\d*Attending"))
    for session in sessions_list:
        user_sessions.append(parse_session(session))
#     user_sessions = user_sessions[::-1]
    
    sessions_list = current_sessions.findAll("div", id=re.compile("sessionListID-\d*Attending"))
    for session in sessions_list:
        user_sessions.append(parse_session(session))
    return user_sessions

def sim_type(string, element):
    for i in string:
        element.send_keys(i)
        pause = np.random.uniform(0,0.1)
        time.sleep(pause)

class itpScraper:
    def __init__(self,
        geckoDriverPath = '/Users/matthewmitchell/Documents/Projects/Tools/Python/Scraping/geckodriver'):
        self.driver = webdriver.Firefox(executable_path=geckoDriverPath)

    def login(self):
        driver = self.driver
        driver.get("https://itp.nyu.edu/camp2023/people")
        time.sleep(np.random.uniform(2,4))
        email_input = driver.find_element_by_id("signin_email")
        password_input = driver.find_element_by_id("signin_password")

        sim_type(itp_creds.u, email_input)
        sim_type(itp_creds.p, password_input)

        signin_button = driver.find_element_by_xpath('//button[text()="Sign In"]')
        signin_button.click()

    def check_for_401(self):
        soup = BeautifulSoup(self.driver.page_source, features="lxml")
        is_401_error = False
        for heading in soup.find_all('h1'):
            if heading.text == "401 Unauthorized":
                is_401_error = True
            else:
                continue
        if is_401_error:
            cur_page = self.driver.current_url
            print("Hit 401 error. Relogging in.")
            self.login()
            time.sleep(2)
            driver.get(cur_page) #Return to original page.
    def parse_all_user_rsvps(self, last_user_scraped=None):
        if last_user_scraped:
            scrape = False #If last_user_scraped is specified do not scrape until found
        driver = self.driver
        driver.get("https://itp.nyu.edu/camp2023/people")
        cur_html = driver.page_source
        soup = BeautifulSoup(cur_html, features="lxml")
        people_divs = soup.find_all("div", {"class": "userListItem"})
        time.sleep(np.random.uniform(1,5))
        user_dict = {}    
        for p_div in people_divs:
            self.check_for_401()
            if scrape:
                try:
                    link = p_div.find_all("a")[0]
                    user_page = "https://itp.nyu.edu/camp2023/" + link.get('href')
                    #Go to user's page
                    driver.get(user_page)
                    #Parse User Page
                    user_sessions = parse_user_sessions(driver)

                    #User Name
                    soup = BeautifulSoup(driver.page_source, features="lxml")
                    user_name = soup.find_all('h1')[-1].text.strip()

                    user_dict[user_name] = user_sessions
                except Exception as e:
                    print("Hit error: {}".format(e))
                    print("Creating temporary save of user_dicts.")
                    time_now = datetime.datetime.now().strftime("%m-%d-%y_%H%M%p")
                    filename = "UserSessionDicts_Temp_{}.pickle".format(time_now)
                    with open(filename, 'wb') as handle:
                        pickle.dump(user_dict, handle, protocol=pickle.HIGHEST_PROTOCOL) 
                
                time.sleep(np.random.uniform(10,30))
                #Return to main page
                driver.get("https://itp.nyu.edu/camp2023/people")
            else:
                profile_info = p_div.find_all("p", {"class":"profileInfo"})[0]
                name = profile_info.get_text().strip().split("   ")[0]
                if name == last_user_scraped:
                    print("Successfully found last person scraped.")
                    scrape = True
                    continue
        time_now = datetime.datetime.now().strftime("%m-%d-%y_%H%M%p")
        filename = "UserSessionDicts_Complete_{}.pickle".format(time_now)
        with open(filename, 'wb') as handle:
            pickle.dump(user_dict, handle, protocol=pickle.HIGHEST_PROTOCOL) 
        return user_dict
