"""Module without deferred annotations that uses forward references."""


class Tree:
    def children(self) -> list["Tree"]:
        """
        Get child nodes.

        Returns:
            The children of this node.
        """
        return []
