import validators
import logger
import os

import pickle

# import queue
import requests
import time


class QueueBot:
    def __init__(self, queue_size=2):
        self.size = queue_size

        self.buffer = []
        self.queue = []
        self.last_checked = 0
        self.last_update = 0  # same as last_checked but for dequeueing
        self.current_state = True

    def fill_buffer(self):
        """
        Fills queue if it is not full
        """
        if len(self.buffer) < self.size:
            response = self.next()

            if response:
                item, cmd = response

                self.buffer.append(item)

                logger.Logger.log_info("Filling up buffer " + item)

                return cmd.format(url=item)
            logger.Logger.log_info("Queue is empty")
        else:
            logger.Logger.log_info("Buffer is full")

    def check_queue(self, command: list):
        """
        Checks to see if command can be removed from buffer
        """

        # if "Queued" in command:
        # for count, each_item in enumerate(self.buffer):
        # logger.Logger.log_info("Queued job detected " + str(each_item))
        # if each_item in command:
        # logger.Logger.log_info("Removed from queue " + each_item)
        # self.queued(each_item)

        if "finished" in command:
            for count, each_item in enumerate(self.buffer):
                logger.Logger.log_info("Finished job detected " + str(each_item))
                if each_item in command:
                    logger.Logger.log_info("Completed job " + each_item)
                    self.finished(each_item)

        if self.last_update + 60 < int(time.time()):
            time.sleep(1)
            logger.Logger.log_info("Checking if anything has finished")
            r = requests.get(
                "http://dashboard.at.ninjawedding.org/logs/recent",
                params={"Accept": "application/json"},
            )
            urls = []
            queuebot_jobs = 0

            for each_job in r.json():
                url = each_job.get("job_data").get("url").rstrip()
                if "queuebot" == each_job.get("job_data").get("started_by").strip():
                    queuebot_jobs += 1
                if not validators.url(url):
                    logger.Logger.log_info("Invalid URL detected " + url)
                else:
                    urls.append(url)

            logger.Logger.log_info(str(queuebot_jobs) + " jobs running")
            logger.Logger.log_info(urls)
            if queuebot_jobs < self.size:
                for count, each_item in enumerate(self.buffer):
                    if not each_item in urls:
                        logger.Logger.log_info(
                            "Completed job (detected through omission) " + each_item
                        )
                        self.finished(each_item)
            self.last_update = int(time.time())

    def next(self):
        """
        Returns a list of the next url
        """
        if len(self.queue) > 0:
            return self.queue.pop()

        # responses = self.sqs.receive_message(
        # QueueUrl=self.queue_uri,
        # AttributeNames=["All"],
        # MaxNumberOfMessages=size,
        # MessageAttributeNames=["All"],
        # VisibilityTimeout=43200,
        # WaitTimeSeconds=10,
        # )

        # logger.Logger.log_info(str(responses)) # debug

        # if responses and responses.get("Messages"):
        # return_tuples = []
        # for each_response in responses.get("Messages"):
        # return_tuples.append((str(each_response.get("Body")), each_response.get("ReceiptHandle")))

        # return return_tuples
        # else:
        # logger.Logger.log_info("Queue is empty!")

    # def queued(self, item: str):
    # """
    # Removes from queue. Not completely done.
    # """
    # self.queue.task_done()

    def finished(self, item: str):
        """
        Removes from buffer, the pr
        """
        self.buffer.remove(item)
        # self.sqs.delete_message(QueueUrl=self.queue_uri, ReceiptHandle=receipt)

    def add(
        self,
        uri: str,
        cmd: str = '!ao < {url} --explain "For maxfan8 - deduplicated automated twitter job started queued with queuebot"',
    ):
        """
        Adds stuff to the queue
        """
        logger.Logger.log_info("Added jobs at " + uri)
        r = requests.get(uri)
        for count, each_line in enumerate(r.content.decode().split()):
            if validators.url(each_line.rstrip()):
                self.queue.append((each_line.rstrip(), cmd))
        return str(count) + " items added to queue."

    def nothing_pending(self) -> bool:
        """
        Returns false if pending, returns true if nothing pending
        Caches every 120 sec
        """
        if self.last_checked + 120 < int(time.time()):
            logger.Logger.log_info("Checking if anything is pending")
            r = requests.get("http://dashboard.at.ninjawedding.org/pending")
            for each_line in r.content.decode().split():
                logger.Logger.log_info(each_line)  # debug
                if "pending-ao" in each_line.rstrip() or each_line.rstrip() == "pending":
                    logger.Logger.log_info("Something in archivebot is pending")
                    self.current_state = False
                    return False
            logger.Logger.log_info("Nothing pending")
            self.current_state = True
            self.last_checked = int(time.time())
            return True
        else:
            logger.Logger.log_info(
                "Fetching from function cache " + str(self.current_state)
            )
            return self.current_state

    def save(self):
        if self.last_checked + self.last_update != 0:  # don't want this to run at first
            with open("state.pickle", "wb") as f:
                logger.Logger.log_info("Saved queuebot state")
                state = (self.buffer, self.queue)
                pickle.dump(state, f)

    def restore(self):
        if os.path.exists("state.pickle"):
            with open("state.pickle", "rb") as f:
                logger.Logger.log_info("Restore queuebot state")
                buffer_list, queue_list = pickle.load(f)

                if buffer_list:
                    self.buffer = buffer_list
                if queue_list:
                    self.queue = queue_list

                logger.Logger.log_info(str(len(self.buffer) + len(self.queue)))

    def poll(self, command=[], restore=False) -> str:
        """
        Polling function
        """
        if restore:
            self.restore()

        if command:
            if command[1] == "add":
                if len(command) == 4:
                    logger.Logger.log_info(
                        "Custom command detected " + command[3].rstrip()
                    )
                    return self.add(command[2].rstrip(), command[3].rstrip())
                else:
                    return self.add(command[2].rstrip())
            elif command[1] == "status":
                return str(len(self.queue) + len(self.buffer)) + " jobs left to go!"
            else:
                return self.check_queue(command)
        else:
            self.check_queue(command)
            if self.nothing_pending():
                return self.fill_buffer()
        return ""
