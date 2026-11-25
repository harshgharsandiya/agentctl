from add import add


def test_add():
    assert add(1, 2, 3) == 6
    assert add(-1, -2, 3) == 0
    assert add(0, 0, 0) == 0

if __name__ == "__main__":
    test_add()
    print("All tests passed.")
