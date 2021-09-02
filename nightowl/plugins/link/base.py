from abc import abstractmethod

from nightowl.plugins import NightOwlPlugin


class LinkBase(NightOwlPlugin):

    @abstractmethod
    def build(self):
        pass
