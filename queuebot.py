import os
import pickle
import time

# import queue
import requests

import logger
import mongoset
import settings
import validators


class QueueBot:
    def __init__(self, queue_size=3):
        self.size = queue_size

        self.buffer = []
        self.queue = []
        self.ab_count = 0
        self.last_checked = 0
        self.last_update = 0  # same as last_checked but for dequeueing
        self.current_state = True

        self.max_cap = 98
        self.min_cap = 94

        self.state = False  # halt or not
        if settings.db_name:
            self.log = mongoset.connect(uri=settings.db_uri, db_name=settings.db_name)[
                "queuebot"
            ]
        else:
            self.log = mongoset.connect(uri=settings.db_uri)["queuebot"]

    def fill_buffer(self):
        """
        Fills queue if it is not full
        """
        if self.state:
            if len(self.buffer) < self.size:
                response = self.next()

                if response:
                    item, cmd = response

                    self.buffer.append(item)

                    logger.Logger.log_info("Filling up buffer " + item)
                    self.heartbeat()

                    return cmd.format(url=item)
                logger.Logger.log_info("Queue is empty")
            else:
                logger.Logger.log_info("Buffer is full")
        else:
            logger.Logger.log_info("Halted")

    def heartbeat(self):
        """
        Updates status
        """
        self.log.upsert(
            {
                "status": True,
                "max_cap": self.max_cap,
                "min_cap": self.min_cap,
                "slots": self.size,
                "last_updated": self.last_update,
                "last_checked": self.last_checked,
                "buffer": self.buffer,
                "queue": self.queue,
                "ab_count": self.ab_count,
            },
            ["status"],
        )

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

        try:
            if self.last_update + 20 < int(time.time()):
                time.sleep(2)
                logger.Logger.log_info("Checking if anything has finished")
                r = requests.get(
                    "http://dashboard.at.ninjawedding.org/logs/recent?count=1",
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
                    elif not each_job.get("job_data").get("finished_at"):
                        urls.append(url)
                    else:
                        logger.Logger.log_info("URL is finished " + url)

                logger.Logger.log_info(
                    str(queuebot_jobs)
                    + " jobs running, "
                    + str(len(urls))
                    + " jobs total on AB."
                )
                self.ab_count = len(urls)
                logger.Logger.log_info(urls)
                if queuebot_jobs < self.size:
                    for count, each_item in enumerate(self.buffer):
                        if not each_item in urls:
                            logger.Logger.log_info(
                                "Completed job (detected through omission) " + each_item
                            )
                            self.finished(each_item)
                if len(urls) < self.min_cap:
                    self.size += 1
                if len(urls) > self.max_cap:
                    if self.size > 0:
                        self.size -= 1

                self.last_update = int(time.time())
            self.heartbeat()

        except Exception as e:
            logger.Logger.log_info("Error!")
            logger.Logger.log_info(e)

        if self.state:
            self.save()

    def next(self):
        """
        Returns a list of the next url
        """
        if self.state:
            if len(self.queue) > 0:
                return self.queue.pop()
        else:
            logger.Logger.log_info("Halted")

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
        if self.state:
            self.log.insert({"item": item, "finished": True})
            self.buffer.remove(item)
        else:
            logger.Logger.log_info("Halted")
        # self.sqs.delete_message(QueueUrl=self.queue_uri, ReceiptHandle=receipt)

    def add(
        self, uri: str, cmd: str = "!ao < {url}",
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
                if (
                    "pending-ao" in each_line.rstrip()
                    or each_line.rstrip() == "pending"
                ):
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
        if self.state:
            if (
                self.last_checked + self.last_update != 0
            ):  # don't want this to run at first
                with open("state.pickle", "wb") as f:
                    logger.Logger.log_info("Saved queuebot state")
                    state = (self.buffer, self.queue)
                    pickle.dump(state, f)
        else:
            logger.Logger.log_info("Halted")

    def restore(self):
        if self.state:
            if os.path.exists("state.pickle"):
                with open("state.pickle", "rb") as f:
                    logger.Logger.log_info("Restore queuebot state")
                    buffer_list, queue_list = pickle.load(f)

                    if buffer_list and len(self.buffer) < len(buffer_list):
                        self.buffer = buffer_list
                    if queue_list and len(self.queue) < len(queue_list):
                        self.queue = queue_list

                    logger.Logger.log_info(str(len(self.buffer) + len(self.queue)))
        else:
            logger.Logger.log_info("Halted")

    def change_slot(self, slot_num: int):
        """
        Changes self.size.
        """
        if slot_num.isdigit():
            orig_size = self.size
            self.size = int(slot_num)
            self.last_checked = 0
            self.last_update = 0
            return "Changed slot size from {orig_size} to {new_size}. Note that the slot size is *roughly* the number of concurrent jobs running. If it's ever significantly out of sync, please let maxfan8 know.".format(
                orig_size=orig_size, new_size=self.size
            )
        else:
            return "TypeError: Please specify a real number"

    def change_capacity(self, command=[]) -> str:
        """
        Change the parameters for the autoscaling capacity feature
        """
        if len(command) == 2 and command[2] == "off":
            self.min_cap = 0
            return "Automatic scaling up has been turned off (by setting min_cap to 0)."
        elif len(command) == 4:
            if command[2].rstrip().isdigit() and command[3].rstrip().isdigit():
                logger.Logger.log_info(
                    "Changing capacity " + command[2] + " " + command[3]
                )
                min_cap = int(command[2].rstrip())
                max_cap = int(command[3].rstrip())
                if min_cap < max_cap:
                    self.min_cap = min_cap
                    self.max_cap = max_cap
                    return "Change autoscaling min_cap to {min_cap} and max_cap to {max_cap}. queuebot will automatically add slots if AB falls below {min_cap} and remove slots if AB goes above {max_cap}".format(
                        min_cap=self.min_cap, max_cap=self.max_cap
                    )
        return "TypeError: Improper capacity command"

    def poll(self, command=[], restore=False) -> str:
        """
        Polling function
        """
        if self.state:
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
                    return str(
                        len(self.queue) + len(self.buffer)
                    ) + " jobs left to go! {slot_size} slots allocated. Min capacity: {min_cap}, max capacity: {max_cap}.".format(
                        slot_size=self.size, max_cap=self.max_cap, min_cap=self.min_cap
                    )
                elif command[1] == "slots":
                    return str(self.change_slot(command[2].rstrip()))
                elif command[1] == "capacity":
                    return str(self.change_capacity(command))
                else:
                    return self.check_queue(command)
            else:
                self.check_queue(command)
                if self.nothing_pending():
                    queued_item = self.fill_buffer()
                    if queued_item:
                        self.log.insert(
                            {
                                "item": queued_item.replace("!ao <", "").rstrip(),
                                "finished": False,
                            }
                        )
                    return queued_item
            return ""
        else:
            logger.Logger.log_info("Halted")
            return ""
