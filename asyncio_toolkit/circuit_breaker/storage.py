import abc


class CircuitBreakerBaseStorage(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, key):
        """
        This method must implement a GET call to a stored value.
        It should return an int value that represents how many times
        this single key has been set.
        """

    @abc.abstractmethod
    def incr(self, key):
        """
        This method must increment 1 int value based in a key stored value.
        It should return an int value that represents how many times
        this single key has been set, after it was incremented by its request.
        """

    @abc.abstractmethod
    def set(self, key, value, timeout):
        """
        This method must add a key with an int value and set a ttl to it
        """
