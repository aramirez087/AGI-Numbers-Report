#!/usr/bin/env python
"""
Simple script to get some CMC and head count telegram data
for the SingularityNET project.

The data is saved into this google spreadsheet and a local SQL Server:
https://docs.google.com/spreadsheets/d/1uEyILbHfPL1MBGIO32tCeLEF1Ndq7BKam4FrksUK6GY/edit#gid=0


Originally written by Alexander Ramirez.
"""
from oauth2client.service_account import ServiceAccountCredentials
import logging, logging.config
from bs4 import BeautifulSoup
from datetime import date
import configparser
import telegram
import requests
import gspread
import tweepy
import praw
import time

# -----------------------------------------Logger config-----------------------------------------
logfilename = './logs/' + time.strftime('%Y%m%d') + '.log'  # this makes one new log file per day
logging.config.fileConfig('log.ini', defaults={'logfilename': logfilename})
logger = logging.getLogger('sLogger')
# -----------------------------------------Program config----------------------------------------
settings = configparser.ConfigParser()
settings.read('config.ini')
bot = telegram.Bot(settings.get('telegram', 'token'))


# Count twitter followers
def get_twitter_followers():
    # Twitter API credentials
    sc = 'twitter'
    consumer_key = settings.get(sc, 'consumer_key')
    consumer_secret = settings.get(sc, 'consumer_secret')
    access_key = settings.get(sc, 'access_key')
    access_secret = settings.get(sc, 'access_secret')
    try:
        logger.info('Preparing to get twitter data...')
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_key, access_secret)
        api = tweepy.API(auth)
        snet_twitter = api.get_user(settings.get(sc, 'username'))
        twitter_followers = snet_twitter.followers_count
        logger.info('--- Found ' + str(twitter_followers) + ' twitter followers.')
        return twitter_followers
    except Exception as e:
        logger.error('Failed to read twitter data: ', exc_info=True)
        return 0


# Count token holders
def get_token_holders():
    try:
        logger.info('Preparing to get token data...')
        response = requests.get(settings.get('ethereum', 'token_url'))
        soup = BeautifulSoup(response.text, 'html.parser')
        holders = [int(s) for s in soup.get_text().splitlines()[44].split() if s.isdigit()][1] #Line 44 has the token holders
        logger.info('--- Found ' + str(holders) + 'token holders.')
        return holders
    except Exception as e:
        logger.error('Failed to obtain token holder count.', exc_info=True)
        return 0


# Get CMC data
def get_cmc_data():
    try:
        logger.info('Preparing to get CMC data...')
        request = requests.get(settings.get('cmc', 'ticker_url'))
        data = request.json()
        logger.info('--- Successfully loaded CMC data.')
        return (data[0]['price_usd'], data[0]['price_btc'], data[0]['24h_volume_usd'],
                data[0]['rank'], data[0]['percent_change_24h'])
    except Exception as e:
        logger.error('Failed to obtain CMC data.', exc_info=True)
        return None


# Get volume rankings from CMC
def get_volume_rank():
    try:
        logger.info('Preparing to get volume rankings...')
        response = requests.get(settings.get('cmc', 'volume_url'))
        soup = BeautifulSoup(response.text, 'html.parser')
        volume_rank = soup.find(id='singularitynet').text.splitlines()[3][:-1]
        logger.info('--- Successfully loaded volume data.')
        return volume_rank
    except Exception as e:
        logger.error('Failed to obtain volume rankings.', exc_info=True)
        return 0


# Count reddit subscribers
def get_reddit_subscribers():
    try:
        logger.info('Preparing to get reddit data...')
        reddit = praw.Reddit(user_agent=settings.get('reddit', 'user_agent'),
                             client_id=settings.get('reddit', 'client_id'),
                             client_secret=settings.get('reddit', 'client_secret'),
                             username=settings.get('reddit', 'username'), password=settings.get('reddit', 'password'))
        reddit_subscribers = reddit.get(settings.get('reddit', 'about_url'), ).subscribers
        logger.info('--- Successfully loaded reddit data.')
        return reddit_subscribers
    except Exception as e:
        logger.error('Failed to obtain reddit data.', exc_info=True)
        return 0


# Count telegram members
def get_telegram_members():
    try:
        logger.info('Preparing to get telegram data...')
        sc = 'telegram'
        tg_community = bot.get_chat_members_count(settings.get(sc, 'community'))  # (SingularityNET Community)
        tg_pricetalk = bot.get_chat_members_count(settings.get(sc, 'pricetalk'))  # (AGI Price Talk)
        tg_devs = bot.get_chat_members_count(settings.get(sc, 'developers'))  # (AGI Developers Community)
        tg_deutschet = bot.get_chat_members_count(settings.get(sc, 'deutschetech'))  # (AGI Deutschland Technologie)
        tg_arvr = bot.get_chat_members_count(settings.get(sc, 'arvr'))  # (AGI AR & VR Technology)
        tg_china = bot.get_chat_members_count(settings.get(sc, 'china'))  # (AGI China)
        tg_france = bot.get_chat_members_count(settings.get(sc, 'france'))  # (AGI France)
        tg_germany = bot.get_chat_members_count(settings.get(sc, 'germany'))  # (AGI AGI Germany)
        tg_holland = bot.get_chat_members_count(settings.get(sc, 'holland'))  # (AGI Holland)
        tg_philos = bot.get_chat_members_count(settings.get(sc, 'philosophers'))  # (AGI Philosophers & Futurism)
        tg_portugal = bot.get_chat_members_count(settings.get(sc, 'portugal'))  # (AGI Portugal)
        tg_russia = bot.get_chat_members_count(settings.get(sc, 'russia'))  # (AGI Russia)
        tg_spain = bot.get_chat_members_count(settings.get(sc, 'spain'))  # (AGI Spain)
        logger.info('--- Successfully loaded telegram data.')
        return (tg_community, tg_pricetalk, tg_devs,
                tg_deutschet, tg_arvr, tg_china,
                tg_france, tg_germany, tg_holland,
                tg_philos, tg_portugal, tg_russia, tg_spain)
    except Exception as e:
        logger.error('Failed to obtain telegram data.', exc_info=True)
        return None


# Save to google spreadsheet
def save_to_spreadsheet(pct_change, price, price_btc, volume, holders, reddit_subscribers, twitter_followers,
                        rank, volume_rank, tg_community, tg_pricetalk, tg_devs, tg_deutschet, tg_arvr, tg_china,
                        tg_france, tg_germany, tg_holland, tg_philos, tg_portugal, tg_russia, tg_spain):
    try:
        logger.info('Preparing to save data to Google...')
        sc = 'google'
        scope = [settings.get(sc, 'scope_a'),
                 settings.get(sc, 'scope_b')]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(settings.get(sc, 'keyfile'), scope)
        gc = gspread.authorize(credentials)
        wks = gc.open(settings.get(sc, 'sheet_name')).sheet1
        report_line = [(date.today() - date(1899, 12, 30)).days, float(pct_change) / 100.00, float(price),
                       float(price_btc), float(volume), float(holders), float(reddit_subscribers),
                       float(twitter_followers), float(rank), float(volume_rank), float(tg_community),
                       float(tg_pricetalk), float(tg_devs), float(tg_deutschet), float(tg_arvr),
                       float(tg_china), float(tg_france), float(tg_germany), float(tg_holland), float(tg_philos),
                       float(tg_portugal), float(tg_russia), float(tg_spain)]
        wks.append_row(report_line)
        logger.info('--- Successfully appended new row.')
    except Exception as e:
        logger.error('Failed to write data to google spreadsheet.', exc_info=True)


# Send a notification when the report is refreshed
def send_notification():
    try:
        logger.info('Waiting for data to be refreshed...')
        time.sleep(10) #Wait 10 seconds
        sc = 'telegram'
        # Notify AGI Price Talk
        bot.send_message(settings.get(sc, 'pricetalk'), text=settings.get(sc, 'notification'))
        logger.info('--- Users have been notified.')
    except Exception as e:
        logger.error('Failed to write data to google spreadsheet.', exc_info=True)


def main():
    logger.info('Program started...')
    # -----------------------------------------------Read the data-----------------------------------------------
    twitter_followers = get_twitter_followers()
    holders = get_token_holders()
    price, price_btc, volume, rank, pct_change = get_cmc_data()
    volume_rank = get_volume_rank()
    reddit_subscribers = get_reddit_subscribers()
    (tg_community, tg_pricetalk, tg_devs,
     tg_deutschet, tg_arvr, tg_china,
     tg_france, tg_germany, tg_holland,
     tg_philos, tg_portugal, tg_russia, tg_spain) = get_telegram_members()
    # -----------------------------------------------Save to google-----------------------------------------------
    save_to_spreadsheet(pct_change, price, price_btc, volume, holders, reddit_subscribers, twitter_followers,
                        rank, volume_rank, tg_community, tg_pricetalk, tg_devs, tg_deutschet, tg_arvr, tg_china,
                        tg_france, tg_germany, tg_holland, tg_philos, tg_portugal, tg_russia, tg_spain)
    # --------------------------------------------------------------------------------------------------------------
    send_notification()
    logger.info('Program finished...')


if __name__ == "__main__":
    # execute only if run as a script
    main()
