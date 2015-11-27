from xmlserdes.errors import TagListComparison


def test_length():
    x = list(map(str, range(10)))
    y = []
    c = TagListComparison(x, y)
    assert len(c) == len(x)


def test_helper_lines():
    x = ['hello-world']
    y = ['hellO-world']
    c = TagListComparison(x, y)
    assert len(c) == 2
    assert str(c) == '[missing: hello-world, unexpected: hellO-world]'
