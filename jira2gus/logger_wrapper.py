import logging

# Switch 3rd party warnings to be redirected to the logging module
logging.captureWarnings(True)

formatter = logging.Formatter('%(asctime)s p%(process)d-t%(thread)d %(levelname)s [%(name)s]: %(message)s')

log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Log in critical cases only to prevent over logging
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)


console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
log.addHandler(console_handler)


def get_logger(name):
    return logging.getLogger(name)


get_logger('loginit').info('inited')
