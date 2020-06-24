# import boto3
import validators
import logger
import pickle
import queue
import requests


class QueueBot:
    def __init__(self, queue_size=2):
        self.size = queue_size

        self.buffer = []
        self.queue = queue.Queue()

        # self.sqs = boto3.client("sqs")
        # self.queue_uri = self.sqs.get_queue_url(QueueName="queuebot.fifo").get(
        # "QueueUrl"
        # )

    def fill_queue(self):
        """
        Fills queue if it is not full
        """
        if len(self.buffer) < self.size:
            item = self.next()

            if item:
                self.buffer.append(item)

                logger.Logger.log_info("Filling up queue " + item)

                return '!ao < {item} --explain "For queuebot - deduplicated automated twitter job"'.format(
                    item=item
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

    def add(self, uri: str):
        """
        Adds stuff to the queue
        """
        logger.Logger.log_info("Added jobs at " + uri)
        r = requests.get(uri)
        for each_line in r.content.decode().split():
            if validators.url(each_line.rstrip()):
                self.queue.put(each_line.rstrip())

    def poll(self, command=[]) -> str:
        """
        Polling function
        """
        if command:
            if command[1] == "add":
                self.add(command[2].rstrip())
            else:
                self.check_queue(command)
        else:
            return self.fill_queue()
        return ""
