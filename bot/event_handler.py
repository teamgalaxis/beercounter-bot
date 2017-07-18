import json
import logging
import re
import requests

logger = logging.getLogger(__name__)


class RtmEventHandler(object):
    def __init__(self, slack_clients, msg_writer):
        self.clients = slack_clients
        self.msg_writer = msg_writer

    def handle(self, event):

        if 'type' in event:
            self._handle_by_type(event['type'], event)

    def _handle_by_type(self, event_type, event):
        if event_type == 'message':
            # message was sent to channel
            self._handle_message(event)

    def _handle_message(self, event):
        # Filter out messages from the bot itself
        #msg_txt = event['text']
        #logging.info("message: {}".format(msg_txt))
        #logging.info("user: {}".format(event))

        if 'text' in event and 'Zahltag' in event['text']:
            self.tell_the_stats(event)

        if 'username' not in event or 'build-bot' not in event['username']:
            return
            
        if 'user' in event and self.clients.is_message_from_me(event['user']) is True:
            # Message from the bot himself
            return 

        msg_txt = event['text']

        failed = self.pipeline_has_failed(event, msg_txt)

        if failed is False:
            return

        self.msg_writer.send_message(event['channel'], "Oh boy, one more beer for the list!")

    def pipeline_has_failed(self, event, message):

        regex = "(Pipeline)\s(#[0-9]+)\s(of)\s(branch)\s([A-Za-z0-9-_]+)\s(by)\s([A-Za-z\s]+)\s(failed)"
    
        m = re.search(regex, message)

        if m is None:
            return False


        logging.info("Pipeline has failed")
        name = m.group(7)

        self.increaseBeerCounterFor(event, name)

        return True

    def tell_the_stats(self, event):

        url = "http://galaxis.rwth-aachen.de/__beercounter/__beercounter.php?action=get"
        r = requests.get(url)

        if r.status_code != 200:
            logging.error("Something went wrong")
            return 

        beer_counter = json.loads(r.content)
        
        for entry in beer_counter:
            msg_txt = "{} = {} beers".format(entry["name"], entry["beers"])
            self.msg_writer.send_message(event['channel'], msg_txt)

    def increaseBeerCounterFor(self, event, name):
        logging.info("Increase for: {}".format(name))
        url = "http://galaxis.rwth-aachen.de/__beercounter/__beercounter.php"
        r = requests.post(url, data={'action': 'add', 'name': name})

        logging.info("{} {}".format(r.status_code, r.reason))

        self.tell_the_stats(event)