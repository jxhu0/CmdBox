class IsolatedControl:
    """Own update boundary, with cheap diagnostics for Flet's eager debug strings."""

    def is_isolated(self):
        return True

    def __repr__(self):
        return f'{type(self).__name__}(id={self._i})'
