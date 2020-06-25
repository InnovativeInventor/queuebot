# import boto3
import validators
import logger
import pickle
import queue
import requests
import time


class QueueBot:
    def __init__(self, queue_size=2):
        self.size = queue_size

        self.buffer = []
        self.queue = queue.Queue()
        self.last_checked = 0
        self.current_state = True

        # self.sqs = boto3.client("sqs")
        # self.queue_uri = self.sqs.get_queue_url(QueueName="queuebot.fifo").get(
        # "QueueUrl"
        # )

    def fill_queue(self):
        """
        Fills queue if it is not full
        """
        if len(self.buffer) < self.size:
            response = self.next()

            if response:
                item, cmd = response

                self.buffer.append(item)

                logger.Logger.log_info("Filling up queue " + item)

                return cmd.format(
                    url=item
                )

    def check_queue(self, command: list):
        """
        Checks to see if command can pop from queue
        """
        if "finished" in command:
            for count, each_item in enumerate(self.buffer):
                logger.Logger.log_info("Finished job detected " + str(each_item))
                if each_item in command:
                    logger.Logger.log_info("Completed job " + each_item)
                    self.finished(each_item)

        elif "Queued" in command:
            for count, each_item in enumerate(self.buffer):
                logger.Logger.log_info("Queued job detected " + str(each_item))
                if each_item in command:
                    logger.Logger.log_info("Removed from queue " + each_item)
                    self.queued(each_item)

    def next(self, size=2):
        """
        Returns a list of the next urls and receipts
        """
        if not self.queue.empty():
            return self.queue.get(timeout=5)

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

    def queued(self, item: str):
        """
        Removes from queue. Not completely done.
        """
        self.queue.task_done()

    def finished(self, item: str):
        """
        Removes from buffer, the pr
        """
        self.buffer.remove(item)
        # self.sqs.delete_message(QueueUrl=self.queue_uri, ReceiptHandle=receipt)

    def add(self, uri: str, cmd : str = '!ao < {url} --explain "For queuebot - deduplicated automated twitter job"'):
        """
        Adds stuff to the queue
        """
        logger.Logger.log_info("Added jobs at " + uri)
        r = requests.get(uri)
        for count, each_line in enumerate(r.content.decode().split()):
            if validators.url(each_line.rstrip()):
                self.queue.put((each_line.rstrip(), cmd))
        return str(count) + "items added to queue."

    def nothing_pending(self) -> bool:
        """
        Returns false if pending, returns true if nothing pending
        Caches every 120 sec
        """
        if self.last_checked + 120 < int(time.time()):
            logger.Logger.log_info("Checking if anything is pending")
            r = requests.get("http://archivebot.com/pending")
            for each_line in r.content.decode().split():
                if "archivebot" in each_line.rstrip():
                    logger.Logger.log_info("Something in archivebot is pending")
                    self.current_state = False
                    return False
            logger.Logger.log_info("Nothing pending")
            self.current_state = True
            return True
        else:
            logger.Logger.log_info("Fetching from function cache " + str(self.current_state))
            return self.current_state


    def poll(self, command=[]) -> str:
        """
        Polling function
        """
        if command:
            if command[1] == "add":
                if len(command) == 4:
                    logger.Logger.log_info("Custom command detected " + command[3].rstrip())
                    return self.add(command[2].rstrip(), command[3].rstrip())
                else:
                    return self.add(command[2].rstrip())
            else:
                return self.check_queue(command)
        else:
            if self.nothing_pending():
                return self.fill_queue()
        return ""
