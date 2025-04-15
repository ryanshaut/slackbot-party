import logging

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.team = getattr(record, 'team', 'unknown_team')
        record.channel = getattr(record, 'channel', 'unknown_channel')
        record.user = getattr(record, 'user', 'unknown_user')
        return True