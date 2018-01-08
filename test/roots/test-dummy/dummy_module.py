import typing


class Class:
    """
    Initializer docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """

    def __init__(self, x: bool, y: int, z: typing.Optional[str]=None):
        pass

    def a_method(self, x: bool, y: int, z: typing.Optional[str]=None) -> str:
        """
        Method docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """
        pass

    @classmethod
    def a_classmethod(cls, x: bool, y: int, z: typing.Optional[str]=None) -> str:
        """
        Classmethod docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """
        pass

    @staticmethod
    def a_staticmethod(x: bool, y: int, z: typing.Optional[str]=None) -> str:
        """
        Staticmethod docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """
        pass

    @property
    def a_property(self) -> str:
        """
        Property docstring
        """
        pass


class DummyException(Exception):
    """
    Exception docstring

    :param message: blah
    """

    def __init__(self, message: str):
        super().__init__(message)


def function(x: bool, y: int, z: typing.Optional[str]=None) -> str:
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """
    pass
